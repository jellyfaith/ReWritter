from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.routers.auth import get_current_user
from app.services.stats_service import (
    get_stats_summary,
    get_daily_trends,
    get_system_status,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
async def get_summary(
    current_user: str = Depends(get_current_user),
) -> dict:
    """获取统计摘要"""
    try:
        summary = await get_stats_summary(current_user)
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计摘要失败: {str(e)}",
        )


@router.get("/daily")
async def get_daily_stats(
    days: Optional[int] = 30,
    current_user: str = Depends(get_current_user),
) -> dict:
    """获取每日趋势数据"""
    try:
        if days <= 0 or days > 365:
            raise ValueError("天数必须在1到365之间")

        trends = await get_daily_trends(current_user, days)
        return trends
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取每日趋势失败: {str(e)}",
        )


@router.get("/system")
async def get_system_stats() -> dict:
    """获取系统状态"""
    try:
        status_info = await get_system_status()
        return status_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统状态失败: {str(e)}",
        )


@router.get("/user/{username}")
async def get_user_stats(
    username: str,
    current_user: str = Depends(get_current_user),
) -> dict:
    """获取指定用户的统计数据（仅管理员）"""
    try:
        # 检查当前用户是否为管理员
        # 这里简化处理，实际应用中需要实现权限检查
        if current_user != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限",
            )

        summary = await get_stats_summary(username)
        return summary
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户统计失败: {str(e)}",
        )