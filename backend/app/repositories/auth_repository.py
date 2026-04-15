from __future__ import annotations

import time
from typing import Any

from pymongo import ASCENDING
from pymongo.collection import Collection

from app.core.settings import AUTH_LIMITS_COLLECTION, AUTH_USERS_COLLECTION
from app.repositories.mongo import get_db


_FAIL_WINDOW_SECONDS = 5 * 60


def users_col() -> Collection[Any]:
    return get_db()[AUTH_USERS_COLLECTION]


def limits_col() -> Collection[Any]:
    return get_db()[AUTH_LIMITS_COLLECTION]


def ensure_auth_indexes() -> None:
    users_col().create_index([("username", ASCENDING)], unique=True)
    limits_col().create_index([("client_id", ASCENDING)], unique=True)


def get_user(username: str) -> dict[str, Any] | None:
    return users_col().find_one({"username": username})


def user_exists(username: str) -> bool:
    return users_col().find_one({"username": username}, {"_id": 1}) is not None


def insert_user(doc: dict[str, Any]) -> None:
    users_col().insert_one(doc)


def get_login_limit(client_id: str) -> dict[str, Any] | None:
    return limits_col().find_one({"client_id": client_id})


def clear_login_limit(client_id: str) -> None:
    limits_col().delete_one({"client_id": client_id})


def save_failed_attempt(client_id: str, max_fails: int, lock_seconds: int) -> None:
    now = time.time()
    current = get_login_limit(client_id) or {}
    recent_attempts = [
        float(ts)
        for ts in current.get("failed_attempts", [])
        if now - float(ts) <= _FAIL_WINDOW_SECONDS
    ]
    recent_attempts.append(now)

    payload: dict[str, Any] = {
        "failed_attempts": recent_attempts,
        "updated_at": now,
    }
    if len(recent_attempts) >= max_fails:
        payload["failed_attempts"] = []
        payload["locked_until"] = now + lock_seconds

    limits_col().update_one(
        {"client_id": client_id},
        {"$set": payload, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
