from __future__ import annotations

import asyncio
import os
from typing import Any

from celery import Celery

from app.agent.graph import AgentState, run_article_workflow


celery_app = Celery(
    "rewritter_agent",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
)


@celery_app.task(name="article.create", bind=True)
def create_article_task(self: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """内容生成任务：串联 LangGraph 的检索、风格融合与草稿生成。"""
    initial_state: AgentState = {
        "topic": str(payload.get("topic", "")),
        "requirements": str(payload.get("requirements", "")),
        "status": "queued",
    }

    result_state = asyncio.run(run_article_workflow(initial_state))

    return {
        "task_id": self.request.id,
        "status": "pending_review",
        "topic": result_state.get("topic", ""),
        "facts": result_state.get("facts", []),
        "style_snippets": result_state.get("style_snippets", []),
        "draft_markdown": result_state.get("draft_markdown", ""),
    }


@celery_app.task(name="article.publish", bind=True)
def publish_article_task(self: Any, task_id: str, article_markdown: str) -> dict[str, str]:
    """发布任务占位：后续接入 Playwright 执行知乎等平台自动发布。"""
    # TODO: 在此处实现登录、草稿填写、提交发布等浏览器自动化流程。
    return {
        "publish_task_id": self.request.id,
        "source_task_id": task_id,
        "status": "published_placeholder",
        "message": f"文章长度 {len(article_markdown)}，发布任务已进入占位流程。",
    }
