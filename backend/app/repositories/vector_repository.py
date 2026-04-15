from __future__ import annotations

from typing import Any

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from app.core.settings import EMBEDDING_DIM, MILVUS_COLLECTION_MATERIALS, MILVUS_HOST, MILVUS_PORT

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
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
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
