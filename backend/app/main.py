from __future__ import annotations

from typing import Any

from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.worker.tasks import celery_app, create_article_task, publish_article_task


class CreateTaskRequest(BaseModel):
    topic: str = Field(min_length=1, description="文章主题")
    requirements: str = Field(default="", description="额外写作要求")


class PublishTaskRequest(BaseModel):
    article_markdown: str = Field(min_length=1, description="审核后的文章正文")


app = FastAPI(
    title="ReWritter-Agent API",
    version="0.1.0",
    description="自动化内容创作与发布系统后端服务",
)

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


@app.post("/api/tasks/create")
async def create_task(request: CreateTaskRequest) -> dict[str, str]:
    payload: dict[str, Any] = request.model_dump()
    task = create_article_task.delay(payload)
    return {"task_id": task.id, "status": "queued"}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
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
async def publish_task(task_id: str, request: PublishTaskRequest) -> dict[str, str]:
    if not task_id.strip():
        raise HTTPException(status_code=400, detail="task_id 不能为空")

    publish_job = publish_article_task.delay(task_id, request.article_markdown)
    return {"publish_task_id": publish_job.id, "status": "publishing"}
