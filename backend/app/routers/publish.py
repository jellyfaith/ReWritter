from __future__ import annotations

import uuid
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field

from app.routers.auth import get_current_user
from app.worker.tasks import publish_article_task
from app.repositories.mongo import get_db
from app.core.settings import PUBLISH_TASKS_COLLECTION


router = APIRouter(prefix="/api/publish", tags=["publish"])


class PublishRequest(BaseModel):
    """发布请求"""
    article_id: Optional[str] = Field(None, description="文章ID（如果已保存）")
    title: str = Field(..., min_length=1, max_length=100, description="文章标题")
    content: str = Field(..., min_length=10, description="文章内容")
    images: Optional[List[str]] = Field([], description="图片路径列表")
    platform: str = Field("xiaohongshu", description="发布平台")


class PublishTaskResponse(BaseModel):
    """发布任务响应"""
    task_id: str
    status: str
    article_title: str
    platform: str
    created_at: float
    estimated_completion_time: Optional[float] = None


class PublishTaskStatus(BaseModel):
    """发布任务状态"""
    task_id: str
    status: str  # pending, processing, published, failed
    article_title: str
    platform: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None


class PublishHistoryItem(BaseModel):
    """发布历史项"""
    task_id: str
    article_title: str
    platform: str
    status: str
    created_at: float
    completed_at: Optional[float] = None
    post_url: Optional[str] = None


class PublishHistoryResponse(BaseModel):
    """发布历史响应"""
    tasks: List[PublishHistoryItem]
    total: int
    page: int
    page_size: int


async def save_publish_task(
    username: str,
    task_id: str,
    article_title: str,
    platform: str,
    article_id: Optional[str] = None
) -> None:
    """保存发布任务到数据库"""
    db = get_db()
    tasks_col = db[PUBLISH_TASKS_COLLECTION]

    task_doc = {
        "task_id": task_id,
        "user_id": username,
        "article_id": article_id,
        "article_title": article_title,
        "platform": platform,
        "status": "pending",
        "created_at": time.time(),
        "updated_at": time.time(),
    }

    tasks_col.insert_one(task_doc)


async def update_publish_task(
    task_id: str,
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None
) -> None:
    """更新发布任务状态"""
    db = get_db()
    tasks_col = db[PUBLISH_TASKS_COLLECTION]

    update_data = {
        "status": status,
        "updated_at": time.time(),
    }

    if status in ["published", "failed"]:
        update_data["completed_at"] = time.time()

    if result:
        update_data["result"] = result

    if error:
        update_data["error"] = error

    tasks_col.update_one(
        {"task_id": task_id},
        {"$set": update_data}
    )


@router.post("/xiaohongshu", response_model=PublishTaskResponse)
async def publish_to_xiaohongshu(
    request: PublishRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
) -> PublishTaskResponse:
    """发布文章到小红书"""
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 准备发布数据
        publish_data = {
            "title": request.title,
            "content": request.content,
            "images": request.images or [],
        }

        # 异步执行发布任务
        publish_article_task.apply_async(
            args=[task_id, publish_data],
            task_id=task_id,
        )

        # 保存任务记录
        await save_publish_task(
            username=current_user,
            task_id=task_id,
            article_title=request.title,
            platform=request.platform,
            article_id=request.article_id,
        )

        return PublishTaskResponse(
            task_id=task_id,
            status="pending",
            article_title=request.title,
            platform=request.platform,
            created_at=time.time(),
            estimated_completion_time=time.time() + 300,  # 预计5分钟完成
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建发布任务失败: {str(e)}",
        )


@router.get("/status/{task_id}", response_model=PublishTaskStatus)
async def get_publish_status(
    task_id: str,
    current_user: str = Depends(get_current_user),
) -> PublishTaskStatus:
    """获取发布任务状态"""
    db = get_db()
    tasks_col = db[PUBLISH_TASKS_COLLECTION]

    task_doc = tasks_col.find_one({
        "task_id": task_id,
        "user_id": current_user,
    })

    if not task_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发布任务不存在",
        )

    # 尝试从Celery获取最新状态
    try:
        from celery.result import AsyncResult
        from app.worker.tasks import celery_app

        celery_task = AsyncResult(task_id, app=celery_app)
        if celery_task.state != task_doc.get("status"):
            # 更新数据库状态
            if celery_task.state == "SUCCESS":
                await update_publish_task(
                    task_id=task_id,
                    status="published",
                    result=celery_task.result,
                )
            elif celery_task.state == "FAILURE":
                await update_publish_task(
                    task_id=task_id,
                    status="failed",
                    error=str(celery_task.result) if celery_task.result else "Unknown error",
                )
            else:
                await update_publish_task(
                    task_id=task_id,
                    status=celery_task.state.lower(),
                )

            # 重新获取更新后的文档
            task_doc = tasks_col.find_one({"task_id": task_id, "user_id": current_user})

    except Exception as e:
        print(f"Failed to get Celery status: {e}")

    return PublishTaskStatus(
        task_id=task_doc["task_id"],
        status=task_doc["status"],
        article_title=task_doc["article_title"],
        platform=task_doc["platform"],
        result=task_doc.get("result"),
        error=task_doc.get("error"),
        created_at=task_doc["created_at"],
        updated_at=task_doc["updated_at"],
        completed_at=task_doc.get("completed_at"),
    )


@router.get("/history", response_model=PublishHistoryResponse)
async def get_publish_history(
    page: int = 1,
    page_size: int = 20,
    platform: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: str = Depends(get_current_user),
) -> PublishHistoryResponse:
    """获取发布历史"""
    db = get_db()
    tasks_col = db[PUBLISH_TASKS_COLLECTION]

    # 构建查询条件
    query = {"user_id": current_user}

    if platform:
        query["platform"] = platform

    if status_filter:
        query["status"] = status_filter

    # 获取总数
    total = tasks_col.count_documents(query)

    # 获取分页数据
    skip = (page - 1) * page_size
    cursor = tasks_col.find(query).sort("created_at", -1).skip(skip).limit(page_size)

    tasks = []
    for doc in cursor:
        tasks.append(PublishHistoryItem(
            task_id=doc["task_id"],
            article_title=doc["article_title"],
            platform=doc["platform"],
            status=doc["status"],
            created_at=doc["created_at"],
            completed_at=doc.get("completed_at"),
            post_url=doc.get("result", {}).get("post_url") if doc.get("result") else None,
        ))

    return PublishHistoryResponse(
        tasks=tasks,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/test")
async def test_publish(
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
) -> dict:
    """测试发布功能"""
    try:
        # 创建测试任务
        task_id = str(uuid.uuid4())

        test_data = {
            "title": "测试发布功能",
            "content": "这是通过API测试的小红书发布功能。\n\n系统正常运行，发布流程已就绪。✨",
            "images": [],
        }

        # 异步执行测试发布
        publish_article_task.apply_async(
            args=[task_id, test_data],
            task_id=task_id,
        )

        # 保存测试任务记录
        await save_publish_task(
            username=current_user,
            task_id=task_id,
            article_title=test_data["title"],
            platform="xiaohongshu",
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "测试发布任务已创建",
            "estimated_time": "约5分钟完成",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试发布失败: {str(e)}",
        )