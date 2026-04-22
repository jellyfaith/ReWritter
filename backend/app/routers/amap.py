from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.schemas import (
    AmapGeocodeRequest,
    AmapGeocodeResponse,
    AmapNearbyRequest,
    AmapPoiItem,
    AmapSearchRequest,
    AmapSearchResponse,
)
from app.services.amap_service import get_amap_service

router = APIRouter(prefix="/api/amap", tags=["amap"])


@router.get("/poi-types", response_model=List[str])
async def get_poi_types(
    service=Depends(get_amap_service)
) -> List[str]:
    """获取支持的POI类型列表"""
    return service.get_poi_types()


@router.post("/search", response_model=AmapSearchResponse)
async def search_places(
    request: AmapSearchRequest,
    service=Depends(get_amap_service)
) -> AmapSearchResponse:
    """地点搜索"""
    try:
        data = service.search_places(
            keywords=request.keywords,
            city=request.city,
            city_limit=request.city_limit,
            page_size=request.page_size,
            page_num=request.page_num
        )

        pois = []
        for poi in data.get("pois", []):
            pois.append(AmapPoiItem(
                id=poi.get("id", ""),
                name=poi.get("name", ""),
                type=poi.get("type", ""),
                address=poi.get("address", ""),
                location=poi.get("location", ""),
                distance=poi.get("distance"),
                tel=poi.get("tel"),
                rating=poi.get("rating")
            ))

        return AmapSearchResponse(
            pois=pois,
            total=int(data.get("count", 0)),
            page=request.page_num,
            page_size=request.page_size
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/nearby", response_model=AmapSearchResponse)
async def search_nearby(
    request: AmapNearbyRequest,
    service=Depends(get_amap_service)
) -> AmapSearchResponse:
    """周边搜索"""
    try:
        data = service.search_nearby(
            location=request.location,
            radius=request.radius,
            types=request.types,
            page_size=request.page_size,
            page_num=request.page_num
        )

        pois = []
        for poi in data.get("pois", []):
            pois.append(AmapPoiItem(
                id=poi.get("id", ""),
                name=poi.get("name", ""),
                type=poi.get("type", ""),
                address=poi.get("address", ""),
                location=poi.get("location", ""),
                distance=poi.get("distance"),
                tel=poi.get("tel"),
                rating=poi.get("rating")
            ))

        return AmapSearchResponse(
            pois=pois,
            total=int(data.get("count", 0)),
            page=request.page_num,
            page_size=request.page_size
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"周边搜索失败: {str(e)}")


@router.post("/geocode", response_model=AmapGeocodeResponse)
async def geocode_address(
    request: AmapGeocodeRequest,
    service=Depends(get_amap_service)
) -> AmapGeocodeResponse:
    """地理编码（地址转坐标）"""
    try:
        data = service.geocode(
            address=request.address,
            city=request.city
        )

        if not data.get("geocodes"):
            raise HTTPException(status_code=404, detail="地址未找到")

        geocode = data["geocodes"][0]
        location = geocode.get("location", "")

        if not location:
            raise HTTPException(status_code=404, detail="无法获取坐标")

        return AmapGeocodeResponse(
            location=location,
            formatted_address=geocode.get("formatted_address", ""),
            country=geocode.get("country", ""),
            province=geocode.get("province", ""),
            city=geocode.get("city", ""),
            district=geocode.get("district", ""),
            township=geocode.get("township")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"地理编码失败: {str(e)}")


@router.post("/reverse-geocode")
async def reverse_geocode(
    location: str,  # "经度,纬度"
    service=Depends(get_amap_service)
) -> dict:
    """逆地理编码（坐标转地址）"""
    try:
        data = service.reverse_geocode(location)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"逆地理编码失败: {str(e)}")


@router.post("/smart-search")
async def smart_search(
    location_name: str,
    city: Optional[str] = None,
    service=Depends(get_amap_service)
) -> dict:
    """智能搜索：获取地点信息及周边POI"""
    try:
        result = service.search_with_fallback(location_name, city)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能搜索失败: {str(e)}")