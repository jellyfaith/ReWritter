from __future__ import annotations

from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_auth
from app.schemas import CreateTaskRequest, PublishTaskRequest
from app.worker.tasks import celery_app, create_article_task, publish_article_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/create")
async def create_task(
    request: CreateTaskRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, str]:
    payload: dict[str, Any] = request.model_dump()
    task = create_article_task.delay(payload)
    return {"task_id": task.id, "status": "queued"}


@router.get("/{task_id}")
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


@router.post("/{task_id}/publish")
async def publish_task(
    task_id: str,
    request: PublishTaskRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, str]:
    if not task_id.strip():
        raise HTTPException(status_code=400, detail="task_id 不能为空")

    publish_job = publish_article_task.delay(task_id, request.article_markdown)
    return {"publish_task_id": publish_job.id, "status": "publishing"}
