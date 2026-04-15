from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services import auth_service


auth_scheme = HTTPBearer(auto_error=False)


async def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme)) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录状态已失效")

    payload = auth_service.verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录状态已失效")

    username = str(payload.get("sub", ""))
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录状态已失效")

    auth_service.require_valid_user(username)
    return payload
