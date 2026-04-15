from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from app.core.settings import MONGODB_DB, MONGODB_URI

_mongo_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _mongo_client.admin.command("ping")
    return _mongo_client


def get_db() -> Database:
    return get_mongo_client()[MONGODB_DB]
