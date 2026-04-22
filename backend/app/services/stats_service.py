from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pymongo import DESCENDING

from app.repositories.mongo import get_db
from app.core.settings import (
    STATISTICS_COLLECTION,
    CHAT_SESSIONS_COLLECTION,
    ARTICLES_COLLECTION,
    WRITING_FLOWS_COLLECTION,
)


async def get_daily_stats(username: str, date_str: Optional[str] = None) -> Dict[str, Any]:
    """获取每日统计数据"""
    db = get_db()
    stats_col = db[STATISTICS_COLLECTION]

    # 如果没有指定日期，使用今天
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 查找当天的统计数据
    stat_doc = stats_col.find_one({
        "user_id": username,
        "date": date_str,
    })

    if stat_doc:
        return {
            "chat_count": stat_doc.get("chat_count", 0),
            "creation_count": stat_doc.get("creation_count", 0),
            "published_count": stat_doc.get("published_count", 0),
            "updated_at": stat_doc.get("updated_at", time.time()),
        }
    else:
        # 如果没有找到，实时计算
        return await calculate_daily_stats(username, date_str)


async def calculate_daily_stats(username: str, date_str: str) -> Dict[str, Any]:
    """实时计算每日统计数据"""
    db = get_db()

    # 计算开始和结束时间戳
    start_date = datetime.strptime(date_str, "%Y-%m-%d")
    end_date = start_date + timedelta(days=1)
    start_ts = time.mktime(start_date.timetuple())
    end_ts = time.mktime(end_date.timetuple())

    # 计算聊天次数
    chat_sessions_col = db[CHAT_SESSIONS_COLLECTION]
    chat_count = chat_sessions_col.count_documents({
        "user_id": username,
        "created_at": {"$gte": start_ts, "$lt": end_ts},
    })

    # 计算创作次数（文章创建）
    articles_col = db[ARTICLES_COLLECTION]
    creation_count = articles_col.count_documents({
        "user_id": username,
        "created_at": {"$gte": start_ts, "$lt": end_ts},
        "status": {"$in": ["draft", "published"]},
    })

    # 计算发布次数
    published_count = articles_col.count_documents({
        "user_id": username,
        "status": "published",
        "created_at": {"$gte": start_ts, "$lt": end_ts},
    })

    # 保存计算结果
    stats_col = db[STATISTICS_COLLECTION]
    stat_doc = {
        "user_id": username,
        "date": date_str,
        "chat_count": chat_count,
        "creation_count": creation_count,
        "published_count": published_count,
        "updated_at": time.time(),
        "calculated_at": time.time(),
    }

    stats_col.update_one(
        {"user_id": username, "date": date_str},
        {"$set": stat_doc},
        upsert=True,
    )

    return stat_doc


async def get_total_stats(username: str) -> Dict[str, Any]:
    """获取总统计数据"""
    db = get_db()

    # 总聊天次数
    chat_sessions_col = db[CHAT_SESSIONS_COLLECTION]
    total_chat_count = chat_sessions_col.count_documents({
        "user_id": username,
    })

    # 总创作次数
    articles_col = db[ARTICLES_COLLECTION]
    total_creation_count = articles_col.count_documents({
        "user_id": username,
        "status": {"$in": ["draft", "published"]},
    })

    # 总发布次数
    total_published_count = articles_col.count_documents({
        "user_id": username,
        "status": "published",
    })

    return {
        "chat_count": total_chat_count,
        "creation_count": total_creation_count,
        "published_count": total_published_count,
    }


async def get_active_tasks_count(username: str) -> int:
    """获取进行中任务数量"""
    db = get_db()
    writing_flows_col = db[WRITING_FLOWS_COLLECTION]

    # 查找状态为进行中的任务
    active_tasks = writing_flows_col.count_documents({
        "user_id": username,
        "status": {"$in": ["queued", "processing"]},
    })

    return active_tasks


async def get_system_status() -> Dict[str, Any]:
    """获取系统状态"""
    # 这里可以添加更复杂的系统健康检查
    # 例如：数据库连接、外部API可用性等

    # 简单的系统状态检查
    try:
        db = get_db()
        # 测试数据库连接
        db.command("ping")

        # 检查关键集合
        required_collections = [
            CHAT_SESSIONS_COLLECTION,
            ARTICLES_COLLECTION,
            STATISTICS_COLLECTION,
        ]

        for collection in required_collections:
            if collection not in db.list_collection_names():
                return {
                    "status": "degraded",
                    "message": f"Collection {collection} missing",
                    "timestamp": time.time(),
                }

        return {
            "status": "healthy",
            "message": "All systems operational",
            "timestamp": time.time(),
        }

    except Exception as e:
        return {
            "status": "down",
            "message": str(e),
            "timestamp": time.time(),
        }


async def get_stats_summary(username: str) -> Dict[str, Any]:
    """获取统计摘要"""
    # 获取今日数据
    today_stats = await get_daily_stats(username)

    # 获取总数据
    total_stats = await get_total_stats(username)

    # 获取进行中任务
    active_tasks = await get_active_tasks_count(username)

    # 获取系统状态
    system_status = await get_system_status()

    return {
        "today": {
            "chat_count": today_stats.get("chat_count", 0),
            "creation_count": today_stats.get("creation_count", 0),
            "published_count": today_stats.get("published_count", 0),
        },
        "total": {
            "chat_count": total_stats.get("chat_count", 0),
            "creation_count": total_stats.get("creation_count", 0),
            "published_count": total_stats.get("published_count", 0),
        },
        "active_tasks": active_tasks,
        "system_status": system_status.get("status", "unknown"),
        "last_updated": time.time(),
    }


async def get_daily_trends(username: str, days: int = 30) -> Dict[str, Any]:
    """获取每日趋势数据"""
    db = get_db()
    stats_col = db[STATISTICS_COLLECTION]

    # 计算开始日期
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 获取日期范围内的统计数据
    cursor = stats_col.find({
        "user_id": username,
        "date": {
            "$gte": start_date.strftime("%Y-%m-%d"),
            "$lte": end_date.strftime("%Y-%m-%d"),
        },
    }).sort("date", 1)

    daily_data = []
    for doc in cursor:
        daily_data.append({
            "date": doc["date"],
            "chat_count": doc.get("chat_count", 0),
            "creation_count": doc.get("creation_count", 0),
            "published_count": doc.get("published_count", 0),
        })

    return {
        "period": f"{days} days",
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily_data": daily_data,
    }


async def update_statistics() -> None:
    """更新统计信息（可由定时任务调用）"""
    db = get_db()
    users_col = db["auth_users"]

    # 获取所有用户
    users = users_col.find({}, {"username": 1})

    for user in users:
        username = user.get("username")
        if username:
            # 更新今日统计
            await get_daily_stats(username)


def ensure_storage() -> None:
    """确保统计集合的索引存在"""
    db = get_db()
    stats_col = db[STATISTICS_COLLECTION]

    # 创建统计集合索引
    stats_col.create_index([("user_id", 1), ("date", 1)], unique=True)
    stats_col.create_index([("date", 1)])
    stats_col.create_index([("user_id", 1), ("updated_at", -1)])