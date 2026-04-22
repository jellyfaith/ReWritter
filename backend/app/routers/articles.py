from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.schemas import (
    ArticleItem,
    ArticleCreateRequest,
    ArticleUpdateRequest,
    ArticleListResponse,
    ArticleVersionItem,
    ArticleDownloadRequest,
)
from app.routers.auth import get_current_user
from app.services.article_service import (
    create_article,
    get_article,
    update_article,
    delete_article,
    list_articles,
    download_article,
    get_article_versions,
    restore_article_version,
)

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("", response_model=ArticleListResponse)
async def get_articles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status_filter: Optional[str] = Query(None, description="状态过滤: draft, published, archived"),
    search: Optional[str] = Query(None, description="搜索标题或内容"),
    current_user: str = Depends(get_current_user),
) -> ArticleListResponse:
    """获取文章列表"""
    try:
        articles, total = await list_articles(
            username=current_user,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            search=search,
        )
        return ArticleListResponse(
            articles=articles,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文章列表失败: {str(e)}",
        )


@router.get("/{article_id}", response_model=ArticleItem)
async def get_article_detail(
    article_id: str,
    current_user: str = Depends(get_current_user),
) -> ArticleItem:
    """获取文章详情"""
    try:
        article = await get_article(article_id, current_user)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章不存在",
            )
        return article
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文章详情失败: {str(e)}",
        )


@router.post("", response_model=ArticleItem, status_code=status.HTTP_201_CREATED)
async def create_new_article(
    request: ArticleCreateRequest,
    current_user: str = Depends(get_current_user),
) -> ArticleItem:
    """创建新文章"""
    try:
        article = await create_article(request, current_user)
        return article
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建文章失败: {str(e)}",
        )


@router.put("/{article_id}", response_model=ArticleItem)
async def update_existing_article(
    article_id: str,
    request: ArticleUpdateRequest,
    current_user: str = Depends(get_current_user),
) -> ArticleItem:
    """更新文章"""
    try:
        article = await update_article(article_id, request, current_user)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章不存在",
            )
        return article
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新文章失败: {str(e)}",
        )


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_article(
    article_id: str,
    current_user: str = Depends(get_current_user),
) -> None:
    """删除文章"""
    try:
        success = await delete_article(article_id, current_user)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章不存在",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文章失败: {str(e)}",
        )


@router.post("/{article_id}/download")
async def download_article_file(
    article_id: str,
    request: ArticleDownloadRequest,
    current_user: str = Depends(get_current_user),
) -> StreamingResponse:
    """下载文章"""
    try:
        article = await get_article(article_id, current_user)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章不存在",
            )

        content = article.content_markdown
        filename = request.filename or f"{article.title}.md"

        # 添加元数据头部
        metadata_header = f"""---
title: {article.title}
author: {current_user}
date: {article.created_at}
status: {article.status}
version: {article.version}
word_count: {article.metadata.word_count}
read_time: {article.metadata.read_time}
tags: {', '.join(article.metadata.tags)}
---

"""
        full_content = metadata_header + content

        return StreamingResponse(
            iter([full_content]),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "Content-Type": "text/markdown; charset=utf-8",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载文章失败: {str(e)}",
        )


@router.get("/{article_id}/versions", response_model=List[ArticleVersionItem])
async def get_article_version_history(
    article_id: str,
    current_user: str = Depends(get_current_user),
) -> List[ArticleVersionItem]:
    """获取文章版本历史"""
    try:
        versions = await get_article_versions(article_id, current_user)
        return versions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文章版本历史失败: {str(e)}",
        )


@router.post("/{article_id}/restore/{version}", response_model=ArticleItem)
async def restore_article_to_version(
    article_id: str,
    version: int,
    current_user: str = Depends(get_current_user),
) -> ArticleItem:
    """恢复文章到指定版本"""
    try:
        article = await restore_article_version(article_id, version, current_user)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章或版本不存在",
            )
        return article
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复文章版本失败: {str(e)}",
        )