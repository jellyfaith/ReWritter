from __future__ import annotations

import uuid
import time
from datetime import datetime
from typing import List, Optional, Tuple
from pymongo import ASCENDING, DESCENDING

from app.schemas import (
    ArticleItem,
    ArticleCreateRequest,
    ArticleUpdateRequest,
    ArticleVersionItem,
    ArticleMetadata,
)
from app.repositories.mongo import get_db
from app.core.settings import ARTICLES_COLLECTION, ARTICLE_VERSIONS_COLLECTION


async def create_article(request: ArticleCreateRequest, username: str) -> ArticleItem:
    """创建新文章"""
    db = get_db()
    articles_col = db[ARTICLES_COLLECTION]
    versions_col = db[ARTICLE_VERSIONS_COLLECTION]

    article_id = str(uuid.uuid4())
    now = time.time()

    # 计算字数和阅读时间
    word_count = len(request.content_markdown.split())
    read_time = f"{max(1, word_count // 300)}分钟"  # 假设每分钟阅读300字

    # 构建文章文档
    article_doc = {
        "article_id": article_id,
        "user_id": username,
        "title": request.title,
        "content_markdown": request.content_markdown,
        "status": request.status or "draft",
        "version": 1,
        "metadata": {
            "word_count": word_count,
            "read_time": read_time,
            "tags": request.tags or [],
            "location_info": request.location_info or None,
        },
        "created_at": now,
        "updated_at": now,
    }

    # 插入文章
    articles_col.insert_one(article_doc)

    # 保存版本历史
    version_doc = {
        "version_id": str(uuid.uuid4()),
        "article_id": article_id,
        "content_markdown": request.content_markdown,
        "version": 1,
        "created_at": now,
    }
    versions_col.insert_one(version_doc)

    # 转换为响应模型
    return ArticleItem(**article_doc)


async def get_article(article_id: str, username: str) -> Optional[ArticleItem]:
    """获取文章详情"""
    db = get_db()
    articles_col = db[ARTICLES_COLLECTION]

    article_doc = articles_col.find_one({
        "article_id": article_id,
        "user_id": username,
    })

    if not article_doc:
        return None

    return ArticleItem(**article_doc)


async def update_article(
    article_id: str,
    request: ArticleUpdateRequest,
    username: str
) -> Optional[ArticleItem]:
    """更新文章"""
    db = get_db()
    articles_col = db[ARTICLES_COLLECTION]
    versions_col = db[ARTICLE_VERSIONS_COLLECTION]

    # 获取当前文章
    current_article = articles_col.find_one({
        "article_id": article_id,
        "user_id": username,
    })

    if not current_article:
        return None

    # 准备更新数据
    update_data = {}
    if request.title is not None:
        update_data["title"] = request.title
    if request.content_markdown is not None:
        update_data["content_markdown"] = request.content_markdown
        # 保存新版本
        version_doc = {
            "version_id": str(uuid.uuid4()),
            "article_id": article_id,
            "content_markdown": request.content_markdown,
            "version": current_article["version"] + 1,
            "created_at": time.time(),
        }
        versions_col.insert_one(version_doc)
        update_data["version"] = current_article["version"] + 1

    if request.status is not None:
        update_data["status"] = request.status

    if request.tags is not None:
        update_data["metadata.tags"] = request.tags

    if request.location_info is not None:
        update_data["metadata.location_info"] = request.location_info

    # 重新计算元数据
    content = update_data.get("content_markdown", current_article.get("content_markdown", ""))
    word_count = len(content.split())
    read_time = f"{max(1, word_count // 300)}分钟"

    update_data["metadata.word_count"] = word_count
    update_data["metadata.read_time"] = read_time
    update_data["updated_at"] = time.time()

    # 执行更新
    result = articles_col.update_one(
        {"article_id": article_id, "user_id": username},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        return None

    # 返回更新后的文章
    updated_article = articles_col.find_one({
        "article_id": article_id,
        "user_id": username,
    })

    return ArticleItem(**updated_article) if updated_article else None


async def delete_article(article_id: str, username: str) -> bool:
    """删除文章"""
    db = get_db()
    articles_col = db[ARTICLES_COLLECTION]

    result = articles_col.delete_one({
        "article_id": article_id,
        "user_id": username,
    })

    return result.deleted_count > 0


async def list_articles(
    username: str,
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> Tuple[List[ArticleItem], int]:
    """获取文章列表"""
    db = get_db()
    articles_col = db[ARTICLES_COLLECTION]

    # 构建查询条件
    query = {"user_id": username}

    if status_filter:
        query["status"] = status_filter

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content_markdown": {"$regex": search, "$options": "i"}},
        ]

    # 获取总数
    total = articles_col.count_documents(query)

    # 获取分页数据
    skip = (page - 1) * page_size
    cursor = articles_col.find(query).sort("updated_at", DESCENDING).skip(skip).limit(page_size)

    articles = [ArticleItem(**doc) for doc in cursor]

    return articles, total


async def download_article(article_id: str, username: str) -> Optional[str]:
    """获取文章下载内容"""
    article = await get_article(article_id, username)
    if not article:
        return None

    return article.content_markdown


async def get_article_versions(article_id: str, username: str) -> List[ArticleVersionItem]:
    """获取文章版本历史"""
    # 首先验证文章存在且属于用户
    article = await get_article(article_id, username)
    if not article:
        return []

    db = get_db()
    versions_col = db[ARTICLE_VERSIONS_COLLECTION]

    cursor = versions_col.find(
        {"article_id": article_id}
    ).sort("version", DESCENDING)

    return [ArticleVersionItem(**doc) for doc in cursor]


async def restore_article_version(
    article_id: str,
    version: int,
    username: str
) -> Optional[ArticleItem]:
    """恢复文章到指定版本"""
    db = get_db()
    articles_col = db[ARTICLES_COLLECTION]
    versions_col = db[ARTICLE_VERSIONS_COLLECTION]

    # 验证文章存在且属于用户
    article = await get_article(article_id, username)
    if not article:
        return None

    # 获取指定版本
    version_doc = versions_col.find_one({
        "article_id": article_id,
        "version": version,
    })

    if not version_doc:
        return None

    # 更新文章内容
    update_data = {
        "content_markdown": version_doc["content_markdown"],
        "updated_at": time.time(),
    }

    result = articles_col.update_one(
        {"article_id": article_id, "user_id": username},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        return None

    # 返回更新后的文章
    updated_article = articles_col.find_one({
        "article_id": article_id,
        "user_id": username,
    })

    return ArticleItem(**updated_article) if updated_article else None

def ensure_storage() -> None:
    """确保文章集合的索引存在"""
    db = get_db()
    articles_col = db[ARTICLES_COLLECTION]
    versions_col = db[ARTICLE_VERSIONS_COLLECTION]

    # 创建文章集合索引
    articles_col.create_index([("article_id", ASCENDING)], unique=True)
    articles_col.create_index([("user_id", ASCENDING)])
    articles_col.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
    articles_col.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])
    articles_col.create_index([("title", "text"), ("content_markdown", "text")])

    # 创建版本集合索引
    versions_col.create_index([("version_id", ASCENDING)], unique=True)
    versions_col.create_index([("article_id", ASCENDING), ("version", DESCENDING)])
    versions_col.create_index([("article_id", ASCENDING), ("created_at", DESCENDING)])
