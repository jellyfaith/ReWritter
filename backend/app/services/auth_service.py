from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

import bcrypt
from fastapi import HTTPException, Request, status

from app.core.settings import AUTH_DEFAULT_PASSWORD, AUTH_USERNAME
from app.repositories import auth_repository

_AUTH_SECRET = secrets.token_urlsafe(32)
_TOKEN_TTL_SECONDS = 8 * 60 * 60
_TOKEN_TTL_REMEMBER_SECONDS = 7 * 24 * 60 * 60
_MAX_FAILS_PER_WINDOW = 5
_LOCK_SECONDS = 10 * 60


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def build_token(username: str, ttl_seconds: int) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": secrets.token_hex(8),
    }
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_AUTH_SECRET.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64url_encode(signature)}"


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        payload_part, signature_part = token.split(".", maxsplit=1)
    except ValueError:
        return None

    expected_sig = hmac.new(_AUTH_SECRET.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    got_sig = _b64url_decode(signature_part)
    if not hmac.compare_digest(expected_sig, got_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None

    sub = str(payload.get("sub", "")).strip()
    if not sub:
        return None

    if int(time.time()) >= int(payload.get("exp", 0)):
        return None

    return payload


def get_client_id(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def ensure_storage() -> None:
    auth_repository.ensure_auth_indexes()
    existing = auth_repository.get_user(AUTH_USERNAME)
    if existing:
        return

    password_hash = bcrypt.hashpw(AUTH_DEFAULT_PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    auth_repository.insert_user(
        {
            "username": AUTH_USERNAME,
            "password_hash": password_hash,
            "role": "admin",
            "created_at": int(time.time()),
        }
    )


def authenticate(username: str, password: str, remember_me: bool, client_id: str) -> tuple[str, int, str, str]:
    limit_doc = auth_repository.get_login_limit(client_id)
    if limit_doc:
        locked_until = float(limit_doc.get("locked_until", 0))
        if time.time() < locked_until:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="登录失败次数过多，请稍后再试")

    user_doc = auth_repository.get_user(username)
    password_hash = "" if not user_doc else str(user_doc.get("password_hash", ""))

    if not password_hash or not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        auth_repository.save_failed_attempt(client_id, _MAX_FAILS_PER_WINDOW, _LOCK_SECONDS)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    auth_repository.clear_login_limit(client_id)
    ttl_seconds = _TOKEN_TTL_REMEMBER_SECONDS if remember_me else _TOKEN_TTL_SECONDS
    username_value = str(user_doc.get("username", username)) if user_doc else username
    role = str(user_doc.get("role", "admin")) if user_doc else "admin"
    token = build_token(username_value, ttl_seconds)
    return token, ttl_seconds, username_value, role


def require_valid_user(username: str) -> None:
    if not auth_repository.user_exists(username):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录状态已失效")


def get_user_preferences(username: str) -> dict[str, Any]:
    """获取用户偏好设置，如果不存在则创建默认值"""
    from app.schemas import UserPreferences

    # 确保用户存在
    require_valid_user(username)

    # 获取或创建偏好设置
    preferences = auth_repository.get_user_preferences(username)
    if preferences:
        return preferences

    # 创建默认偏好
    default_prefs = UserPreferences().dict()
    now = time.time()
    default_prefs["created_at"] = now
    default_prefs["updated_at"] = now

    # 保存默认偏好
    auth_repository.update_user_preferences(username, default_prefs)
    return default_prefs


def update_user_preferences(username: str, preferences_update: dict[str, Any]) -> dict[str, Any]:
    """更新用户偏好设置"""
    from app.schemas import UserPreferences, UserPreferencesUpdateRequest

    # 确保用户存在
    require_valid_user(username)

    # 获取当前偏好
    current_prefs = get_user_preferences(username)

    # 使用Pydantic模型验证更新
    # 首先创建完整的当前偏好对象
    current_model = UserPreferences(**current_prefs)

    # 创建更新对象并应用更新
    update_dict = {k: v for k, v in preferences_update.items() if v is not None}
    updated_model = current_model.copy(update=update_dict)

    # 更新时间戳
    now = time.time()
    updated_dict = updated_model.dict()
    updated_dict["updated_at"] = now

    # 保存更新
    success = auth_repository.update_user_preferences(username, updated_dict)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户偏好失败"
        )

    return updated_dict
