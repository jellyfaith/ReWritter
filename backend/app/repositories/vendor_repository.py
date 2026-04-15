from __future__ import annotations

from pymongo import ASCENDING, ReturnDocument

from app.core.settings import VENDOR_CONFIGS_COLLECTION
from app.repositories.mongo import get_db


_collection = None


def get_vendor_collection():
    global _collection
    if _collection is None:
        _collection = get_db()[VENDOR_CONFIGS_COLLECTION]
    return _collection


def ensure_vendor_indexes() -> None:
    collection = get_vendor_collection()
    collection.create_index(
        [("username", ASCENDING), ("capability", ASCENDING)],
        unique=True,
        name="uniq_username_capability",
    )


def list_configs(username: str) -> list[dict]:
    collection = get_vendor_collection()
    return list(collection.find({"username": username}, {"_id": 0}).sort("updated_at", ASCENDING))


def get_config(username: str, capability: str) -> dict | None:
    collection = get_vendor_collection()
    return collection.find_one({"username": username, "capability": capability}, {"_id": 0})


def upsert_config(username: str, capability: str, payload: dict) -> dict:
    collection = get_vendor_collection()
    updated = collection.find_one_and_update(
        {"username": username, "capability": capability},
        {"$set": payload, "$setOnInsert": {"username": username, "capability": capability, "created_at": payload["updated_at"]}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    return updated or {}
