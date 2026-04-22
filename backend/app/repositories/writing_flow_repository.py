from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection

from app.core.settings import WRITING_FLOWS_COLLECTION
from app.repositories.mongo import get_db


def flows_col() -> Collection[Any]:
    return get_db()[WRITING_FLOWS_COLLECTION]


def ensure_writing_flow_indexes() -> None:
    flows_col().create_index([("flow_id", ASCENDING)], unique=True)
    flows_col().create_index([("username", ASCENDING), ("updated_at", ASCENDING)])


def create_flow(doc: dict[str, Any]) -> None:
    flows_col().insert_one(doc)


def get_flow(flow_id: str, username: str) -> dict[str, Any] | None:
    return flows_col().find_one({"flow_id": flow_id, "username": username})


def update_flow(flow_id: str, username: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    return flows_col().find_one_and_update(
        {"flow_id": flow_id, "username": username},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )
