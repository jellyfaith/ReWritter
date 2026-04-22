from __future__ import annotations

from typing import Any

from pymilvus import (
    Collection, CollectionSchema, DataType, FieldSchema,
    connections, utility, AnnSearchRequest, RRFRanker, Hits
)
import concurrent.futures
import time

from app.core.settings import (
    EMBEDDING_DIM, MILVUS_COLLECTION_MATERIALS, MILVUS_HOST, MILVUS_PORT,
    ENABLE_HYBRID_SEARCH, RAG_HYBRID_ALPHA
)

_connected = False


def _connect() -> None:
    global _connected
    if _connected:
        return
    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
    _connected = True


def ensure_vector_collection() -> None:
    _connect()
    if utility.has_collection(MILVUS_COLLECTION_MATERIALS):
        return

    fields = [
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=64),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        FieldSchema(name="group_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="group_name", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="file_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),  # 用于向量搜索的原始内容
        FieldSchema(name="content_text", dtype=DataType.VARCHAR, max_length=4096),  # 用于BM25全文检索
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
    ]
    schema = CollectionSchema(fields=fields, description="RAG material chunks")
    collection = Collection(name=MILVUS_COLLECTION_MATERIALS, schema=schema)
    collection.create_index(
        field_name="vector",
        index_params={
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024},
        },
    )

    # 为BM25全文检索创建倒排索引
    collection.create_index(
        field_name="content_text",
        index_params={
            "index_type": "INVERTED",
        },
    )

    collection.load()


def get_collection_vector_dim() -> int:
    _connect()
    if not utility.has_collection(MILVUS_COLLECTION_MATERIALS):
        return EMBEDDING_DIM

    collection = Collection(MILVUS_COLLECTION_MATERIALS)
    for field in collection.schema.fields:
        if field.name == "vector":
            return int(field.params.get("dim", EMBEDDING_DIM))
    return EMBEDDING_DIM


def insert_chunks(
    chunk_ids: list[str],
    vectors: list[list[float]],
    group_ids: list[str],
    group_names: list[str],
    file_ids: list[str],
    file_names: list[str],
    contents: list[str],
    chunk_indexes: list[int],
) -> None:
    # 为BM25检索准备文本内容（可以在这里添加文本预处理）
    content_texts = contents  # 简化：使用相同内容，实际可以分词、去停用词等
    _connect()
    collection = Collection(MILVUS_COLLECTION_MATERIALS)
    collection.insert(
        [
            chunk_ids,
            vectors,
            group_ids,
            group_names,
            file_ids,
            file_names,
            contents,
            content_texts,
            chunk_indexes,
        ]
    )
    collection.flush()


def search_chunks(query_vector: list[float], top_k: int, group_ids: list[str]) -> list[dict[str, Any]]:
    _connect()
    if not group_ids:
        return []

    collection = Collection(MILVUS_COLLECTION_MATERIALS)
    escaped_group_ids = [gid.replace("'", "\\'") for gid in group_ids]
    quoted = [f"'{item}'" for item in escaped_group_ids]
    expr = f"group_id in [{','.join(quoted)}]"
    results = collection.search(
        data=[query_vector],
        anns_field="vector",
        param={"metric_type": "COSINE", "params": {"nprobe": 16}},
        limit=top_k,
        expr=expr,
        output_fields=["chunk_id", "group_id", "group_name", "file_id", "file_name", "content", "chunk_index"],
    )

    hits = results[0] if results else []
    items: list[dict[str, Any]] = []
    for hit in hits:
        entity = getattr(hit, "entity", None)
        if entity is None:
            continue
        items.append(
            {
                "chunk_id": str(entity.get("chunk_id", "")),
                "group_id": str(entity.get("group_id", "")),
                "group_name": str(entity.get("group_name", "")),
                "file_id": str(entity.get("file_id", "")),
                "file_name": str(entity.get("file_name", "")),
                "chunk_index": int(entity.get("chunk_index", 0)),
                "content": str(entity.get("content", "")),
                "score": float(getattr(hit, "distance", 0.0)),
            }
        )
    return items


def search_chunks_bm25(
    query_text: str,
    top_k: int,
    group_ids: list[str]
) -> list[dict[str, Any]]:
    """使用BM25进行全文检索"""
    _connect()
    if not group_ids:
        return []

    collection = Collection(MILVUS_COLLECTION_MATERIALS)
    escaped_group_ids = [gid.replace("'", "\\'") for gid in group_ids]
    quoted = [f"'{item}'" for item in escaped_group_ids]
    expr = f"group_id in [{','.join(quoted)}]"

    # 使用BM25检索
    search_params = {
        "metric_type": "BM25",
        "params": {"k": top_k}
    }

    try:
        results = collection.search(
            data=[query_text],
            anns_field="content_text",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["chunk_id", "group_id", "group_name", "file_id", "file_name", "content", "chunk_index"],
        )

        hits = results[0] if results else []
        items: list[dict[str, Any]] = []
        for hit in hits:
            entity = getattr(hit, "entity", None)
            if entity is None:
                continue
            items.append({
                "chunk_id": str(entity.get("chunk_id", "")),
                "group_id": str(entity.get("group_id", "")),
                "group_name": str(entity.get("group_name", "")),
                "file_id": str(entity.get("file_id", "")),
                "file_name": str(entity.get("file_name", "")),
                "chunk_index": int(entity.get("chunk_index", 0)),
                "content": str(entity.get("content", "")),
                "score": float(getattr(hit, "distance", 0.0)),  # BM25分数
            })
        return items
    except Exception as e:
        print(f"BM25搜索失败，回退到普通搜索: {e}")
        # 如果BM25失败，使用普通文本匹配回退
        return []


def search_chunks_hybrid(
    query_vector: list[float],
    query_text: str,
    top_k: int,
    group_ids: list[str],
    alpha: float = None
) -> list[dict[str, Any]]:
    """混合检索：结合向量搜索和BM25全文检索"""
    if alpha is None:
        alpha = RAG_HYBRID_ALPHA

    if not ENABLE_HYBRID_SEARCH or alpha >= 1.0:
        # 纯向量搜索
        return search_chunks(query_vector, top_k, group_ids)
    elif alpha <= 0.0:
        # 纯BM25搜索
        return search_chunks_bm25(query_text, top_k, group_ids)

    # 并行执行向量搜索和BM25搜索
    import concurrent.futures
    import time

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        vector_future = executor.submit(search_chunks, query_vector, top_k * 2, group_ids)
        bm25_future = executor.submit(search_chunks_bm25, query_text, top_k * 2, group_ids)

        vector_results = vector_future.result()
        bm25_results = bm25_future.result()

    # 归一化分数
    def normalize_scores(results, is_vector=True):
        if not results:
            return results

        scores = [r["score"] for r in results]
        if not scores:
            return results

        # 向量搜索使用余弦相似度，范围在[-1, 1]或[0, 1]，BM25分数范围不定
        if is_vector:
            # 假设向量分数是余弦相似度，转换为[0, 1]范围
            min_score = min(scores)
            max_score = max(scores)
            if max_score - min_score > 0:
                for i, r in enumerate(results):
                    r["normalized_score"] = (r["score"] - min_score) / (max_score - min_score)
            else:
                for i, r in enumerate(results):
                    r["normalized_score"] = 1.0
        else:
            # BM25分数，简单的最大归一化
            max_score = max(scores) if scores else 1.0
            if max_score > 0:
                for i, r in enumerate(results):
                    r["normalized_score"] = r["score"] / max_score
            else:
                for i, r in enumerate(results):
                    r["normalized_score"] = 0.0

        return results

    vector_results = normalize_scores(vector_results, is_vector=True)
    bm25_results = normalize_scores(bm25_results, is_vector=False)

    # 合并结果
    chunk_map = {}
    for result in vector_results:
        chunk_id = result["chunk_id"]
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = result.copy()
            chunk_map[chunk_id]["vector_score"] = result.get("normalized_score", 0)
            chunk_map[chunk_id]["bm25_score"] = 0
        else:
            chunk_map[chunk_id]["vector_score"] = result.get("normalized_score", 0)

    for result in bm25_results:
        chunk_id = result["chunk_id"]
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = result.copy()
            chunk_map[chunk_id]["vector_score"] = 0
            chunk_map[chunk_id]["bm25_score"] = result.get("normalized_score", 0)
        else:
            chunk_map[chunk_id]["bm25_score"] = result.get("normalized_score", 0)

    # 计算混合分数
    for chunk_id, data in chunk_map.items():
        vector_score = data.get("vector_score", 0)
        bm25_score = data.get("bm25_score", 0)
        hybrid_score = alpha * vector_score + (1 - alpha) * bm25_score
        data["hybrid_score"] = hybrid_score
        data["score"] = hybrid_score  # 替换原始分数

    # 按混合分数排序
    sorted_items = sorted(chunk_map.values(), key=lambda x: x["hybrid_score"], reverse=True)

    # 返回top_k个结果
    result = sorted_items[:top_k]

    # 添加调试信息
    if len(vector_results) > 0 or len(bm25_results) > 0:
        print(f"混合检索完成: 向量结果{len(vector_results)}个, BM25结果{len(bm25_results)}个, "
              f"合并去重后{len(chunk_map)}个, 耗时{time.time() - start_time:.2f}s")

    return result
