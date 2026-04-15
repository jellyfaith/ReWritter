from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI

from app.api.deps import require_auth
from app.schemas import (
    DeepSeekVendorTestRequest,
    DeepSeekVendorTestResponse,
    EmbeddingVendorTestResponse,
    VendorConfigItem,
    VendorConfigUpdateRequest,
)
from app.services import chat_service, vendor_service

router = APIRouter(prefix="/api/vendors", tags=["vendors"])


@router.get("/configs", response_model=list[VendorConfigItem])
async def list_vendor_configs(
    _auth: dict[str, Any] = Depends(require_auth),
) -> list[VendorConfigItem]:
    username = str(_auth.get("sub", "")).strip()
    return [VendorConfigItem(**item) for item in vendor_service.get_display_configs(username)]


@router.put("/configs/{capability}", response_model=VendorConfigItem)
async def upsert_vendor_config(
    capability: str,
    payload: VendorConfigUpdateRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> VendorConfigItem:
    username = str(_auth.get("sub", "")).strip()
    normalized_capability = capability.strip().lower()
    if payload.capability != normalized_capability:
        raise HTTPException(status_code=400, detail="路径 capability 与请求体不一致")
    saved = vendor_service.save_config(
        username=username,
        capability=payload.capability,
        vendor_id=payload.vendor_id,
        display_name=payload.display_name,
        api_base=payload.api_base,
        api_key=payload.api_key,
        model=payload.model,
        enabled=payload.enabled,
    )
    return VendorConfigItem(**saved)


@router.post("/deepseek/test", response_model=DeepSeekVendorTestResponse)
async def test_deepseek_vendor_connectivity(
    request: DeepSeekVendorTestRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> DeepSeekVendorTestResponse:
    username = str(_auth.get("sub", "")).strip()
    started_at = time.perf_counter()
    try:
        _, resolved_model = chat_service.run_llm_chat(
            messages=[{"role": "user", "content": "ping"}],
            model=request.model,
            enable_thinking=request.enable_thinking,
            username=username,
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        message = str(getattr(exc, "detail", str(exc)))
        return DeepSeekVendorTestResponse(
            ok=False,
            model=request.model,
            configured="DEEPSEEK_API_KEY" not in message,
            latency_ms=latency_ms,
            message=message,
        )

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    return DeepSeekVendorTestResponse(
        ok=True,
        model=resolved_model,
        configured=True,
        latency_ms=latency_ms,
        message="连接测试通过",
    )


@router.post("/embedding/test", response_model=EmbeddingVendorTestResponse)
async def test_embedding_vendor_connectivity(
    _auth: dict[str, Any] = Depends(require_auth),
) -> EmbeddingVendorTestResponse:
    username = str(_auth.get("sub", "")).strip()
    started_at = time.perf_counter()
    resolved = vendor_service.resolve_embedding_vendor(username)
    api_key = str(resolved.get("api_key", "")).strip()
    api_base = str(resolved.get("api_base", "")).strip()
    model = str(resolved.get("model", "")).strip()
    vendor = str(resolved.get("vendor_id", "embedding"))

    if not api_key:
        return EmbeddingVendorTestResponse(
            ok=False,
            vendor=vendor,
            model=model,
            configured=False,
            latency_ms=0,
            message="未配置 embedding 厂家 API Key",
        )

    try:
        client = OpenAI(api_key=api_key, base_url=api_base)
        response = client.embeddings.create(model=model, input=["ping"])
        ok = bool(getattr(response, "data", None))
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        return EmbeddingVendorTestResponse(
            ok=ok,
            vendor=vendor,
            model=model,
            configured=True,
            latency_ms=latency_ms,
            message="连接测试通过" if ok else "服务返回为空",
        )
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        return EmbeddingVendorTestResponse(
            ok=False,
            vendor=vendor,
            model=model,
            configured=True,
            latency_ms=latency_ms,
            message=f"连接测试失败: {exc}",
        )
