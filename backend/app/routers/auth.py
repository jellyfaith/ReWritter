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
