from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection

from app.core.settings import MATERIAL_CHUNKS_COLLECTION, MATERIAL_FILES_COLLECTION, MATERIAL_GROUPS_COLLECTION
from app.repositories.mongo import get_db


def groups_col() -> Collection[Any]:
    return get_db()[MATERIAL_GROUPS_COLLECTION]


def files_col() -> Collection[Any]:
    return get_db()[MATERIAL_FILES_COLLECTION]


def chunks_col() -> Collection[Any]:
    return get_db()[MATERIAL_CHUNKS_COLLECTION]


def ensure_material_indexes() -> None:
    groups_col().create_index([("group_id", ASCENDING)], unique=True)
    groups_col().create_index([("group_name", ASCENDING), ("username", ASCENDING)], unique=True)
    files_col().create_index([("file_id", ASCENDING)], unique=True)
    files_col().create_index([("group_id", ASCENDING), ("username", ASCENDING)])
    chunks_col().create_index([("chunk_id", ASCENDING)], unique=True)
    chunks_col().create_index([("group_id", ASCENDING), ("username", ASCENDING)])
    chunks_col().create_index([("file_id", ASCENDING), ("username", ASCENDING)])
    chunks_col().create_index(
        [("content", "text"), ("file_name", "text")],
        name="chunks_text_search",
        default_language="none",
    )


def list_groups(username: str) -> list[dict[str, Any]]:
    return list(groups_col().find({"username": username}).sort("updated_at", -1))


def get_group(group_name: str, username: str) -> dict[str, Any] | None:
    return groups_col().find_one({"group_name": group_name, "username": username})


def get_group_by_id(group_id: str, username: str) -> dict[str, Any] | None:
    return groups_col().find_one({"group_id": group_id, "username": username})


def create_group(doc: dict[str, Any]) -> None:
    groups_col().insert_one(doc)


def touch_group(group_id: str, username: str, chunk_delta: int, file_delta: int, updated_at: int) -> dict[str, Any] | None:
    return groups_col().find_one_and_update(
        {"group_id": group_id, "username": username},
        {
            "$inc": {
                "file_count": file_delta,
                "chunk_count": chunk_delta,
            },
            "$set": {"updated_at": updated_at},
        },
        return_document=ReturnDocument.AFTER,
    )


def create_file(doc: dict[str, Any]) -> None:
    files_col().insert_one(doc)


def create_chunks(docs: list[dict[str, Any]]) -> None:
    if not docs:
        return
    chunks_col().insert_many(docs)


def list_files(group_id: str, username: str) -> list[dict[str, Any]]:
    return list(files_col().find({"group_id": group_id, "username": username}).sort("created_at", -1))


def search_chunks_by_keywords(
    username: str,
    query: str,
    group_ids: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    normalized_query = query.strip()
    if not normalized_query or not group_ids:
        return []

    filter_doc: dict[str, Any] = {
        "username": username,
        "group_id": {"$in": group_ids},
        "$text": {"$search": normalized_query},
    }
    projection = {
        "_id": 0,
        "chunk_id": 1,
        "group_id": 1,
        "group_name": 1,
        "file_id": 1,
        "file_name": 1,
        "chunk_index": 1,
        "content": 1,
        "score": {"$meta": "textScore"},
    }
    return list(
        chunks_col()
        .find(filter_doc, projection)
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )
