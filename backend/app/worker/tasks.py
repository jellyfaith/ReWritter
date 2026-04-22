from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from celery import Celery

from app.agent.graph import AgentState, run_article_workflow
from app.services.xiaohongshu_publisher import XiaohongshuPublisher


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
def publish_article_task(self: Any, task_id: str, article_data: dict[str, Any]) -> dict[str, Any]:
    """发布文章到小红书"""
    try:
        print(f"Starting publish task for article: {task_id}")

        # 创建发布器实例
        publisher = XiaohongshuPublisher()

        # 异步执行发布
        result = asyncio.run(publisher.publish_article(article_data))

        return {
            "publish_task_id": self.request.id,
            "source_task_id": task_id,
            "status": "published" if result.get("success") else "failed",
            "success": result.get("success", False),
            "post_url": result.get("post_url"),
            "error": result.get("error"),
            "draft_saved": result.get("draft_saved", False),
            "title": article_data.get("title", ""),
            "content_length": len(article_data.get("content", "")),
            "timestamp": time.time(),
        }
    except Exception as e:
        print(f"Publish task failed: {e}")
        return {
            "publish_task_id": self.request.id,
            "source_task_id": task_id,
            "status": "failed",
            "success": False,
            "error": str(e),
            "timestamp": time.time(),
        }
