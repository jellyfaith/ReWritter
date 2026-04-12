from __future__ import annotations

import base64
import bcrypt
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from app.worker.tasks import celery_app, create_article_task, publish_article_task


class CreateTaskRequest(BaseModel):
    topic: str = Field(min_length=1, description="文章主题")
    requirements: str = Field(default="", description="额外写作要求")


class PublishTaskRequest(BaseModel):
    article_markdown: str = Field(min_length=1, description="审核后的文章正文")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict[str, str]


AUTH_USERNAME = os.getenv("AUTH_ADMIN_USERNAME", "admin")
_DEFAULT_PASSWORD = os.getenv("AUTH_ADMIN_PASSWORD", "admin123")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "rewritter")
AUTH_USERS_COLLECTION = os.getenv("AUTH_USERS_COLLECTION", "auth_users")
AUTH_LIMITS_COLLECTION = os.getenv("AUTH_LIMITS_COLLECTION", "auth_login_limits")

_mongo_client: MongoClient | None = None
_auth_users_col: Collection[Any] | None = None
_auth_limits_col: Collection[Any] | None = None

_AUTH_SECRET = os.getenv("AUTH_TOKEN_SECRET", "")
if not _AUTH_SECRET:
    _AUTH_SECRET = secrets.token_urlsafe(32)

_TOKEN_TTL_SECONDS = 8 * 60 * 60
_TOKEN_TTL_REMEMBER_SECONDS = 7 * 24 * 60 * 60

_FAIL_WINDOW_SECONDS = 5 * 60
_MAX_FAILS_PER_WINDOW = 5
_LOCK_SECONDS = 10 * 60

auth_scheme = HTTPBearer(auto_error=False)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def _build_token(username: str, ttl_seconds: int) -> str:
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


def _verify_token(token: str) -> dict[str, Any] | None:
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

    now = int(time.time())
    if now >= int(payload.get("exp", 0)):
        return None

    return payload


def _get_client_id(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _get_auth_collections() -> tuple[Collection[Any], Collection[Any]]:
    global _mongo_client, _auth_users_col, _auth_limits_col

    if _auth_users_col is not None and _auth_limits_col is not None:
        return _auth_users_col, _auth_limits_col

    _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    _mongo_client.admin.command("ping")
    db = _mongo_client[MONGODB_DB]
    _auth_users_col = db[AUTH_USERS_COLLECTION]
    _auth_limits_col = db[AUTH_LIMITS_COLLECTION]
    return _auth_users_col, _auth_limits_col


def _seed_admin_user() -> None:
    users_col, limits_col = _get_auth_collections()
    users_col.create_index([("username", ASCENDING)], unique=True)
    limits_col.create_index([("client_id", ASCENDING)], unique=True)

    existing = users_col.find_one({"username": AUTH_USERNAME}, {"_id": 1})
    if existing:
        return

    hashed = bcrypt.hashpw(_DEFAULT_PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    users_col.insert_one(
        {
            "username": AUTH_USERNAME,
            "password_hash": hashed,
            "role": "admin",
            "created_at": int(time.time()),
        }
    )


def _get_user_by_username(username: str) -> dict[str, Any] | None:
    users_col, _ = _get_auth_collections()
    return users_col.find_one({"username": username})


def _is_locked(client_id: str) -> bool:
    _, limits_col = _get_auth_collections()
    doc = limits_col.find_one({"client_id": client_id}, {"locked_until": 1})
    if not doc:
        return False
    locked_until = float(doc.get("locked_until", 0))
    return time.time() < locked_until


def _record_failed_attempt(client_id: str) -> None:
    now = time.time()
    _, limits_col = _get_auth_collections()
    doc = limits_col.find_one({"client_id": client_id}, {"failed_attempts": 1}) or {}
    recent_attempts = [
        float(ts)
        for ts in doc.get("failed_attempts", [])
        if now - float(ts) <= _FAIL_WINDOW_SECONDS
    ]
    recent_attempts.append(now)

    update_doc: dict[str, Any] = {
        "failed_attempts": recent_attempts,
        "updated_at": now,
    }
    if len(recent_attempts) >= _MAX_FAILS_PER_WINDOW:
        update_doc["failed_attempts"] = []
        update_doc["locked_until"] = now + _LOCK_SECONDS

    limits_col.update_one(
        {"client_id": client_id},
        {"$set": update_doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


def _clear_failed_attempts(client_id: str) -> None:
    _, limits_col = _get_auth_collections()
    limits_col.delete_one({"client_id": client_id})


def _user_exists(username: str) -> bool:
    users_col, _ = _get_auth_collections()
    return users_col.find_one({"username": username}, {"_id": 1}) is not None


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录状态已失效")

    payload = _verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录状态已失效")

    username = str(payload.get("sub", ""))
    if not username or not _user_exists(username):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录状态已失效")

    return payload


app = FastAPI(
    title="ReWritter-Agent API",
    version="0.1.0",
    description="自动化内容创作与发布系统后端服务",
)


@app.on_event("startup")
async def setup_auth_storage() -> None:
    try:
        _seed_admin_user()
    except Exception as exc:
        raise RuntimeError(f"MongoDB 鉴权存储初始化失败: {exc}") from exc

# 允许前端控制台在开发阶段跨域访问后端接口。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest) -> LoginResponse:
    client_id = _get_client_id(request)

    if _is_locked(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登录失败次数过多，请稍后再试",
        )

    user_doc = _get_user_by_username(payload.username)
    password_hash_raw = "" if not user_doc else str(user_doc.get("password_hash", ""))

    if not password_hash_raw or not bcrypt.checkpw(
        payload.password.encode("utf-8"),
        password_hash_raw.encode("utf-8"),
    ):
        _record_failed_attempt(client_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    _clear_failed_attempts(client_id)
    ttl_seconds = _TOKEN_TTL_REMEMBER_SECONDS if payload.remember_me else _TOKEN_TTL_SECONDS
    username = str(user_doc.get("username", payload.username)) if user_doc else payload.username
    role = str(user_doc.get("role", "admin")) if user_doc else "admin"
    token = _build_token(username, ttl_seconds)
    return LoginResponse(
        access_token=token,
        expires_in=ttl_seconds,
        user={"username": username, "role": role},
    )


@app.post("/api/tasks/create")
async def create_task(
    request: CreateTaskRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, str]:
    payload: dict[str, Any] = request.model_dump()
    task = create_article_task.delay(payload)
    return {"task_id": task.id, "status": "queued"}


@app.get("/api/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    _auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.state == "PENDING":
        return {"task_id": task_id, "state": task_result.state, "result": None}

    if task_result.failed():
        return {
            "task_id": task_id,
            "state": task_result.state,
            "error": str(task_result.result),
        }

    return {
        "task_id": task_id,
        "state": task_result.state,
        "result": task_result.result,
    }


@app.post("/api/tasks/{task_id}/publish")
async def publish_task(
    task_id: str,
    request: PublishTaskRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, str]:
    if not task_id.strip():
        raise HTTPException(status_code=400, detail="task_id 不能为空")

    publish_job = publish_article_task.delay(task_id, request.article_markdown)
    return {"publish_task_id": publish_job.id, "status": "publishing"}
