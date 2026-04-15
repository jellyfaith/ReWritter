from __future__ import annotations

from typing import Any

from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection

from app.core.settings import CHAT_MESSAGES_COLLECTION, CHAT_SESSIONS_COLLECTION
from app.repositories.mongo import get_db


def sessions_col() -> Collection[Any]:
    return get_db()[CHAT_SESSIONS_COLLECTION]


def messages_col() -> Collection[Any]:
    return get_db()[CHAT_MESSAGES_COLLECTION]


def ensure_chat_indexes() -> None:
    sessions_col().create_index([("session_id", ASCENDING)], unique=True)
    sessions_col().create_index([("username", ASCENDING), ("updated_at", ASCENDING)])
    messages_col().create_index([("message_id", ASCENDING)], unique=True)
    messages_col().create_index([("session_id", ASCENDING), ("created_at", ASCENDING)])


def create_session(doc: dict[str, Any]) -> None:
    sessions_col().insert_one(doc)


def get_session(session_id: str, username: str) -> dict[str, Any] | None:
    return sessions_col().find_one({"session_id": session_id, "username": username})


def list_sessions(username: str, limit: int = 100) -> list[dict[str, Any]]:
    cursor = sessions_col().find({"username": username}).sort("updated_at", -1).limit(limit)
    return list(cursor)


def rename_session(session_id: str, username: str, title: str, updated_at: int) -> dict[str, Any] | None:
    return sessions_col().find_one_and_update(
        {"session_id": session_id, "username": username},
        {"$set": {"title": title, "updated_at": updated_at}},
        return_document=ReturnDocument.AFTER,
    )


def delete_session(session_id: str, username: str) -> bool:
    deleted = sessions_col().find_one_and_delete({"session_id": session_id, "username": username})
    if not deleted:
        return False
    messages_col().delete_many({"session_id": session_id})
    return True


def insert_message(doc: dict[str, Any]) -> None:
    messages_col().insert_one(doc)


def list_messages(session_id: str) -> list[dict[str, Any]]:
    return list(messages_col().find({"session_id": session_id}).sort("created_at", 1))


def list_prompt_messages(session_id: str, limit: int = 30) -> list[dict[str, Any]]:
    return list(messages_col().find({"session_id": session_id}).sort("created_at", 1).limit(limit))


def touch_session(session_id: str, username: str, title: str, model: str, enable_thinking: bool, updated_at: int) -> dict[str, Any] | None:
    sessions_col().update_one(
        {"session_id": session_id, "username": username},
        {
            "$set": {
                "updated_at": updated_at,
                "title": title,
                "model": model,
                "enable_thinking": enable_thinking,
            }
        },
    )
    return sessions_col().find_one({"session_id": session_id, "username": username})
