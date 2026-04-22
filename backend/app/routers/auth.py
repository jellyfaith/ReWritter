from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas import LoginRequest, LoginResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest) -> LoginResponse:
    client_id = auth_service.get_client_id(request)
    token, expires_in, username, role = auth_service.authenticate(
        username=payload.username,
        password=payload.password,
        remember_me=payload.remember_me,
        client_id=client_id,
    )
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user={"username": username, "role": role},
    )


from fastapi import Depends, Header, HTTPException
from app.schemas import UserPreferencesResponse, UserPreferencesUpdateRequest


async def get_current_user(authorization: str = Header(None)) -> str:
    """从Authorization头获取当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")

    token = authorization[7:]  # 移除"Bearer "前缀
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="认证令牌无效")

    return username


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    current_user: str = Depends(get_current_user)
) -> UserPreferencesResponse:
    """获取当前用户的偏好设置"""
    preferences = auth_service.get_user_preferences(current_user)
    return UserPreferencesResponse(preferences=preferences)


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    update_request: UserPreferencesUpdateRequest,
    current_user: str = Depends(get_current_user)
) -> UserPreferencesResponse:
    """更新当前用户的偏好设置"""
    preferences = auth_service.update_user_preferences(
        current_user,
        update_request.dict(exclude_unset=True)
    )
    return UserPreferencesResponse(preferences=preferences)
