from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import require_auth
from app.schemas import (
    MaterialFileItem,
    MaterialGroupItem,
    MaterialRetrieveRequest,
    MaterialRetrieveResponse,
    MaterialUploadResponse,
)
from app.services import material_service

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("/groups", response_model=list[MaterialGroupItem])
async def list_material_groups(
    _auth: dict[str, Any] = Depends(require_auth),
) -> list[MaterialGroupItem]:
    username = str(_auth.get("sub", "")).strip()
    return [material_service.serialize_group(doc) for doc in material_service.list_groups(username)]


@router.get("/groups/{group_id}/files", response_model=list[MaterialFileItem])
async def list_material_files(
    group_id: str,
    _auth: dict[str, Any] = Depends(require_auth),
) -> list[MaterialFileItem]:
    username = str(_auth.get("sub", "")).strip()
    return [material_service.serialize_file(doc) for doc in material_service.list_group_files(group_id, username)]


@router.post("/upload", response_model=MaterialUploadResponse)
async def upload_material(
    group_name: str = Form(...),
    topic: str = Form(""),
    file: UploadFile = File(...),
    _auth: dict[str, Any] = Depends(require_auth),
) -> MaterialUploadResponse:
    username = str(_auth.get("sub", "")).strip()
    file_bytes = await file.read()
    group_doc, file_doc, embedding_provider = material_service.upload_material(
        username=username,
        group_name=group_name,
        topic=topic,
        file_name=file.filename or "unnamed.txt",
        content_bytes=file_bytes,
    )
    return MaterialUploadResponse(
        group=material_service.serialize_group(group_doc),
        file=material_service.serialize_file(file_doc),
        embedding_provider=embedding_provider,
        message="素材上传并向量化完成",
    )


@router.post("/retrieve", response_model=MaterialRetrieveResponse)
async def retrieve_material_chunks(
    payload: MaterialRetrieveRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> MaterialRetrieveResponse:
    username = str(_auth.get("sub", "")).strip()
    items = material_service.retrieve_material_chunks(
        username=username,
        query=payload.query,
        group_id=payload.group_id,
        top_k=payload.top_k,
    )
    return MaterialRetrieveResponse(items=items)
