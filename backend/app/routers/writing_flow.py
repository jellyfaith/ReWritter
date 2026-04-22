from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.schemas import (
    SevenStepConfirmOutlineRequest,
    SevenStepConfirmTitleRequest,
    SevenStepCreateRequest,
    SevenStepFlowItem,
)
from app.services import writing_flow_service

router = APIRouter(prefix="/api/writing-flow", tags=["writing-flow"])


@router.post("/sessions", response_model=SevenStepFlowItem)
async def create_flow(
    payload: SevenStepCreateRequest,
    auth_payload: dict[str, Any] = Depends(require_auth),
) -> SevenStepFlowItem:
    username = str(auth_payload.get("sub", ""))
    return writing_flow_service.create_flow(
        username=username,
        topic=payload.topic,
        preferences=payload.preferences,
        style=payload.style,
    )


@router.get("/sessions/{flow_id}", response_model=SevenStepFlowItem)
async def get_flow(
    flow_id: str,
    auth_payload: dict[str, Any] = Depends(require_auth),
) -> SevenStepFlowItem:
    username = str(auth_payload.get("sub", ""))
    return writing_flow_service.get_flow(username=username, flow_id=flow_id)


@router.post("/sessions/{flow_id}/confirm-title", response_model=SevenStepFlowItem)
async def confirm_title(
    flow_id: str,
    payload: SevenStepConfirmTitleRequest,
    auth_payload: dict[str, Any] = Depends(require_auth),
) -> SevenStepFlowItem:
    username = str(auth_payload.get("sub", ""))
    return writing_flow_service.confirm_title(
        username=username,
        flow_id=flow_id,
        main_title=payload.main_title,
        sub_title=payload.sub_title,
    )


@router.post("/sessions/{flow_id}/confirm-outline", response_model=SevenStepFlowItem)
async def confirm_outline(
    flow_id: str,
    payload: SevenStepConfirmOutlineRequest,
    auth_payload: dict[str, Any] = Depends(require_auth),
) -> SevenStepFlowItem:
    username = str(auth_payload.get("sub", ""))
    return writing_flow_service.confirm_outline(
        username=username,
        flow_id=flow_id,
        outline=payload.outline,
    )
