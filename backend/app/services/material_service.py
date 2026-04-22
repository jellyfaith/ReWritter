from __future__ import annotations

import hashlib
import logging
import secrets
import time
from typing import Any

from fastapi import HTTPException
from openai import OpenAI

from app.core.settings import (
    EMBEDDING_MODEL,
    ENABLE_HYBRID_SEARCH,
    RAG_CANDIDATE_POOL,
    RAG_HYBRID_ALPHA,
)
from app.repositories import material_repository, vector_repository
from app.schemas import MaterialFileItem, MaterialGroupItem, MaterialRetrieveItem
from app.services import vendor_service

logger = logging.getLogger(__name__)


def ensure_storage() -> None:
    material_repository.ensure_material_indexes()
    vector_repository.ensure_vector_collection()


def _split_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    total = len(normalized)
    while start < total:
        end = min(total, start + chunk_size)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= total:
            break
        start = max(0, end - overlap)
    return chunks


def _normalize_embedding_dim(vector: list[float], target_dim: int) -> list[float]:
    if len(vector) == target_dim:
        return vector
    if len(vector) > target_dim:
        return vector[:target_dim]
    return vector + [0.0] * (target_dim - len(vector))


def _fallback_embedding(text: str, target_dim: int) -> list[float]:
    base = hashlib.sha256(text.encode("utf-8")).digest()
    vector: list[float] = []
    for i in range(target_dim):
        b = base[i % len(base)]
        vector.append((float(b) / 255.0) * 2.0 - 1.0)
    return vector


def _embed_chunks(chunks: list[str], username: str, target_dim: int) -> tuple[list[list[float]], str]:
    if not chunks:
        return [], "none"

    resolved = vendor_service.resolve_embedding_vendor(username)
    api_key = str(resolved.get("api_key", "")).strip()
    api_base = str(resolved.get("api_base", "")).strip()
    model = str(resolved.get("model", "")).strip() or EMBEDDING_MODEL

    if not api_key:
        return [_fallback_embedding(item, target_dim) for item in chunks], "fallback-hash"

    client = OpenAI(api_key=api_key, base_url=api_base)
    try:
        response = client.embeddings.create(model=model, input=chunks)
        vectors = [_normalize_embedding_dim(list(item.embedding), target_dim) for item in response.data]
        return vectors, model
    except Exception:
        return [_fallback_embedding(item, target_dim) for item in chunks], "fallback-hash"


def _embed_query(text: str, username: str, target_dim: int) -> tuple[list[float], str]:
    vectors, provider = _embed_chunks([text], username, target_dim)
    if not vectors:
        return _fallback_embedding(text, target_dim), "fallback-hash"
    return vectors[0], provider


def serialize_group(doc: dict[str, Any]) -> MaterialGroupItem:
    return MaterialGroupItem(
        group_id=str(doc.get("group_id", "")),
        group_name=str(doc.get("group_name", "")),
        topic=str(doc.get("topic", "")),
        file_count=int(doc.get("file_count", 0)),
        chunk_count=int(doc.get("chunk_count", 0)),
        created_at=int(doc.get("created_at", 0)),
        updated_at=int(doc.get("updated_at", 0)),
    )


def serialize_file(doc: dict[str, Any]) -> MaterialFileItem:
    return MaterialFileItem(
        file_id=str(doc.get("file_id", "")),
        group_id=str(doc.get("group_id", "")),
        file_name=str(doc.get("file_name", "")),
        file_size=int(doc.get("file_size", 0)),
        chunk_count=int(doc.get("chunk_count", 0)),
        created_at=int(doc.get("created_at", 0)),
    )


def list_groups(username: str) -> list[dict[str, Any]]:
    return material_repository.list_groups(username)


def list_group_files(group_id: str, username: str) -> list[dict[str, Any]]:
    group_doc = material_repository.get_group_by_id(group_id, username)
    if not group_doc:
        raise HTTPException(status_code=404, detail="素材组不存在")
    return material_repository.list_files(group_id, username)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _normalize_score_items(items: list[dict[str, Any]]) -> dict[str, float]:
    if not items:
        return {}
    score_map: dict[str, float] = {}
    raw_scores: list[float] = []
    for item in items:
        chunk_id = str(item.get("chunk_id", ""))
        if not chunk_id:
            continue
        score = float(item.get("score", 0.0))
        score_map[chunk_id] = score
        raw_scores.append(score)

    if not score_map:
        return {}
    min_score = min(raw_scores)
    max_score = max(raw_scores)
    if max_score - min_score < 1e-8:
        return {key: 1.0 for key in score_map}
    return {key: (value - min_score) / (max_score - min_score) for key, value in score_map.items()}


def _dedupe_by_chunk(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        chunk_id = str(item.get("chunk_id", ""))
        if not chunk_id:
            continue
        existing = deduped.get(chunk_id)
        if existing is None or float(item.get("score", 0.0)) > float(existing.get("score", 0.0)):
            deduped[chunk_id] = item
    return list(deduped.values())


def retrieve_material_chunks(
    username: str,
    query: str,
    group_id: str | None,
    top_k: int,
    search_type: str = "vector",
    alpha: float | None = None,
    candidate_pool: int | None = None,
) -> list[MaterialRetrieveItem]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    user_groups = material_repository.list_groups(username)
    allowed_group_ids = [str(item.get("group_id", "")) for item in user_groups if str(item.get("group_id", ""))]
    if group_id:
        if group_id not in allowed_group_ids:
            raise HTTPException(status_code=404, detail="素材组不存在")
        search_group_ids = [group_id]
    else:
        search_group_ids = allowed_group_ids

    if not search_group_ids:
        return []

    search_started_at = time.perf_counter()
    target_dim = vector_repository.get_collection_vector_dim()
    query_vector, _ = _embed_query(normalized_query, username, target_dim)

    resolved_search_type = search_type if search_type in {"vector", "hybrid", "keyword"} else "vector"
    if resolved_search_type == "hybrid" and not ENABLE_HYBRID_SEARCH:
        resolved_search_type = "vector"

    resolved_alpha = _clamp(alpha if alpha is not None else RAG_HYBRID_ALPHA, 0.0, 1.0)
    resolved_pool = max(top_k, candidate_pool if candidate_pool is not None else RAG_CANDIDATE_POOL)

    vector_docs: list[dict[str, Any]] = []
    keyword_docs: list[dict[str, Any]] = []

    if resolved_search_type in {"vector", "hybrid"}:
        vector_docs = vector_repository.search_chunks(
            query_vector=query_vector,
            top_k=resolved_pool,
            group_ids=search_group_ids,
        )

    if resolved_search_type in {"keyword", "hybrid"}:
        keyword_docs = material_repository.search_chunks_by_keywords(
            username=username,
            query=normalized_query,
            group_ids=search_group_ids,
            limit=resolved_pool,
        )

    if resolved_search_type == "vector":
        selected = _dedupe_by_chunk(vector_docs)[:top_k]
    elif resolved_search_type == "keyword":
        selected = _dedupe_by_chunk(keyword_docs)[:top_k]
    else:
        vector_norm = _normalize_score_items(vector_docs)
        keyword_norm = _normalize_score_items(keyword_docs)

        merged: dict[str, dict[str, Any]] = {}
        for item in vector_docs:
            chunk_id = str(item.get("chunk_id", ""))
            if not chunk_id:
                continue
            merged[chunk_id] = dict(item)
        for item in keyword_docs:
            chunk_id = str(item.get("chunk_id", ""))
            if not chunk_id:
                continue
            if chunk_id not in merged:
                merged[chunk_id] = dict(item)

        scored: list[dict[str, Any]] = []
        for chunk_id, item in merged.items():
            score = (resolved_alpha * vector_norm.get(chunk_id, 0.0)) + ((1.0 - resolved_alpha) * keyword_norm.get(chunk_id, 0.0))
            item["score"] = score
            scored.append(item)

        scored.sort(key=lambda doc: float(doc.get("score", 0.0)), reverse=True)
        selected = _dedupe_by_chunk(scored)[:top_k]

    elapsed_ms = int((time.perf_counter() - search_started_at) * 1000)
    logger.info(
        "rag_retrieve strategy=%s groups=%d vector_candidates=%d keyword_candidates=%d selected=%d elapsed_ms=%d",
        resolved_search_type,
        len(search_group_ids),
        len(vector_docs),
        len(keyword_docs),
        len(selected),
        elapsed_ms,
    )
    return [MaterialRetrieveItem(**item) for item in selected]


def build_rag_context(
    username: str,
    query: str,
    group_id: str | None,
    top_k: int,
    search_type: str = "vector",
    alpha: float | None = None,
    candidate_pool: int | None = None,
) -> tuple[str, list[MaterialRetrieveItem]]:
    items = retrieve_material_chunks(
        username=username,
        query=query,
        group_id=group_id,
        top_k=top_k,
        search_type=search_type,
        alpha=alpha,
        candidate_pool=candidate_pool,
    )
    if not items:
        return "", []

    context_lines: list[str] = []
    for idx, item in enumerate(items, start=1):
        context_lines.append(
            f"[{idx}] 来源组:{item.group_name} 文件:{item.file_name} 片段:{item.chunk_index}\n{item.content}"
        )
    context_text = "\n\n".join(context_lines)
    return context_text, items


def upload_material(username: str, group_name: str, topic: str, file_name: str, content_bytes: bytes) -> tuple[dict[str, Any], dict[str, Any], str]:
    if not group_name.strip():
        raise HTTPException(status_code=400, detail="group_name 不能为空")
    if not file_name.strip():
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = file_name.lower().rsplit(".", maxsplit=1)[-1] if "." in file_name else ""
    if ext not in {"txt", "md", "markdown"}:
        raise HTTPException(status_code=400, detail="仅支持 txt / md / markdown 文件")

    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = content_bytes.decode("utf-8", errors="ignore")

    chunks = _split_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="文件内容为空，无法向量化")

    target_dim = vector_repository.get_collection_vector_dim()
    vectors, embedding_provider = _embed_chunks(chunks, username, target_dim)

    group_doc = material_repository.get_group(group_name.strip(), username)
    now = int(time.time())
    if not group_doc:
        group_doc = {
            "group_id": f"mgrp_{secrets.token_hex(8)}",
            "group_name": group_name.strip(),
            "topic": topic.strip() or group_name.strip(),
            "username": username,
            "file_count": 0,
            "chunk_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        material_repository.create_group(group_doc)

    file_doc = {
        "file_id": f"mfile_{secrets.token_hex(8)}",
        "group_id": str(group_doc.get("group_id", "")),
        "username": username,
        "file_name": file_name,
        "file_size": len(content_bytes),
        "chunk_count": len(chunks),
        "created_at": now,
    }
    material_repository.create_file(file_doc)

    chunk_ids = [f"mchunk_{secrets.token_hex(8)}" for _ in chunks]
    group_ids = [str(group_doc.get("group_id", "")) for _ in chunks]
    group_names = [str(group_doc.get("group_name", "")) for _ in chunks]
    file_ids = [str(file_doc.get("file_id", "")) for _ in chunks]
    file_names = [file_name for _ in chunks]
    chunk_indexes = list(range(len(chunks)))

    vector_repository.insert_chunks(
        chunk_ids=chunk_ids,
        vectors=vectors,
        group_ids=group_ids,
        group_names=group_names,
        file_ids=file_ids,
        file_names=file_names,
        contents=chunks,
        chunk_indexes=chunk_indexes,
    )

    chunk_docs = [
        {
            "chunk_id": chunk_ids[idx],
            "group_id": group_ids[idx],
            "group_name": group_names[idx],
            "file_id": file_ids[idx],
            "file_name": file_names[idx],
            "chunk_index": chunk_indexes[idx],
            "content": chunks[idx],
            "username": username,
            "created_at": now,
        }
        for idx in range(len(chunks))
    ]
    material_repository.create_chunks(chunk_docs)

    updated_group = material_repository.touch_group(
        group_id=str(group_doc.get("group_id", "")),
        username=username,
        chunk_delta=len(chunks),
        file_delta=1,
        updated_at=now,
    )
    if not updated_group:
        raise HTTPException(status_code=500, detail="素材组更新失败")

    return updated_group, file_doc, embedding_provider
