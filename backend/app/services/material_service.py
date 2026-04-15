from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from fastapi import HTTPException
from openai import OpenAI

from app.core.settings import (
    EMBEDDING_MODEL,
)
from app.repositories import material_repository, vector_repository
from app.schemas import MaterialFileItem, MaterialGroupItem, MaterialRetrieveItem
from app.services import vendor_service


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


def retrieve_material_chunks(username: str, query: str, group_id: str | None, top_k: int) -> list[MaterialRetrieveItem]:
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

    target_dim = vector_repository.get_collection_vector_dim()
    query_vector, _ = _embed_query(normalized_query, username, target_dim)
    docs = vector_repository.search_chunks(query_vector=query_vector, top_k=top_k, group_ids=search_group_ids)
    return [MaterialRetrieveItem(**item) for item in docs]


def build_rag_context(username: str, query: str, group_id: str | None, top_k: int) -> tuple[str, list[MaterialRetrieveItem]]:
    items = retrieve_material_chunks(username, query, group_id, top_k)
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
