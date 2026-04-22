from __future__ import annotations

import json
import time
from typing import Any, List, Optional
from urllib.parse import urlencode

import redis
import requests
from fastapi import HTTPException

from app.core.settings import (
    AMAP_API_KEY,
    AMAP_BASE_URL,
    AMAP_CACHE_TTL,
    CELERY_BROKER_URL,
)


class AmapService:
    """高德地图服务，封装高德地图Web API，提供地点搜索、周边搜索等功能"""

    def __init__(self):
        self.api_key = AMAP_API_KEY
        self.base_url = AMAP_BASE_URL.rstrip("/")
        self.cache_ttl = AMAP_CACHE_TTL

        # 初始化Redis缓存
        try:
            # 从CELERY_BROKER_URL提取Redis连接信息
            # CELERY_BROKER_URL格式: redis://redis:6379/0
            redis_url = CELERY_BROKER_URL.replace("redis://", "").split("/")[0]
            host_port = redis_url.split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 6379
            self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
            self.redis_client.ping()  # 测试连接
        except Exception as e:
            print(f"Redis连接失败，将禁用缓存: {e}")
            self.redis_client = None

    def _get_cache_key(self, endpoint: str, params: dict) -> str:
        """生成缓存键"""
        sorted_params = sorted(params.items())
        param_str = urlencode(sorted_params)
        return f"amap:{endpoint}:{param_str}"

    def _cache_get(self, cache_key: str) -> Optional[dict]:
        """从缓存获取数据"""
        if not self.redis_client:
            return None

        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None

    def _cache_set(self, cache_key: str, data: dict) -> None:
        """设置缓存"""
        if not self.redis_client:
            return

        try:
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(data, ensure_ascii=False)
            )
        except Exception:
            pass

    def _make_request(self, endpoint: str, params: dict) -> dict:
        """向高德地图API发送请求"""
        if not self.api_key or self.api_key == "your_amap_api_key_here":
            raise HTTPException(
                status_code=400,
                detail="高德地图API密钥未配置，请设置AMAP_API_KEY环境变量"
            )

        # 添加API密钥和输出格式
        params = params.copy()
        params["key"] = self.api_key
        params["output"] = "JSON"

        cache_key = self._get_cache_key(endpoint, params)

        # 检查缓存
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 检查API返回状态
            if data.get("status") != "1":
                error_msg = data.get("info", "未知错误")
                raise HTTPException(status_code=400, detail=f"高德地图API错误: {error_msg}")

            # 缓存结果
            self._cache_set(cache_key, data)
            return data

        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="高德地图API请求超时")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"高德地图API请求失败: {e}")

    def search_places(
        self,
        keywords: str,
        city: Optional[str] = None,
        city_limit: bool = True,
        page_size: int = 20,
        page_num: int = 1
    ) -> dict:
        """
        地点搜索API
        文档: https://lbs.amap.com/api/webservice/guide/api/search/#text

        Args:
            keywords: 查询关键词
            city: 城市名称/城市编码
            city_limit: 是否限制在指定城市内搜索
            page_size: 每页记录数
            page_num: 页码

        Returns:
            API响应数据
        """
        params = {
            "keywords": keywords,
            "page": page_num,
            "offset": page_size,
            "citylimit": "true" if city_limit else "false",
        }
        if city:
            params["city"] = city

        return self._make_request("place/text", params)

    def search_nearby(
        self,
        location: str,  # "经度,纬度"
        radius: int = 3000,
        types: Optional[str] = None,
        page_size: int = 20,
        page_num: int = 1
    ) -> dict:
        """
        周边搜索API
        文档: https://lbs.amap.com/api/webservice/guide/api/search/#around

        Args:
            location: 中心点坐标，格式: "经度,纬度"
            radius: 搜索半径，单位: 米，范围: 0-50000
            types: POI类型，多个类型用"|"分隔
            page_size: 每页记录数
            page_num: 页码

        Returns:
            API响应数据
        """
        params = {
            "location": location,
            "radius": radius,
            "page": page_num,
            "offset": page_size,
        }
        if types:
            params["types"] = types

        return self._make_request("place/around", params)

    def geocode(
        self,
        address: str,
        city: Optional[str] = None
    ) -> dict:
        """
        地理编码API（地址转坐标）
        文档: https://lbs.amap.com/api/webservice/guide/api/georegeo/#geo

        Args:
            address: 地址
            city: 城市名称/城市编码

        Returns:
            API响应数据
        """
        params = {"address": address}
        if city:
            params["city"] = city

        return self._make_request("geocode/geo", params)

    def reverse_geocode(
        self,
        location: str  # "经度,纬度"
    ) -> dict:
        """
        逆地理编码API（坐标转地址）
        文档: https://lbs.amap.com/api/webservice/guide/api/georegeo/#regeo

        Args:
            location: 坐标，格式: "经度,纬度"

        Returns:
            API响应数据
        """
        params = {"location": location}
        return self._make_request("geocode/regeo", params)

    def get_poi_types(self) -> List[str]:
        """
        获取POI类型列表
        返回预定义的20个常用POI类型
        """
        return [
            "餐饮服务", "购物服务", "生活服务", "旅游景点",
            "体育休闲", "医疗保健", "住宿服务", "商务住宅",
            "政府机构", "交通设施", "金融保险", "公司企业",
            "道路附属", "地名地址", "室内设施", "通行设施",
            "汽车服务", "汽车销售", "汽车维修", "摩托车服务"
        ]

    def search_with_fallback(
        self,
        location_name: str,
        city: Optional[str] = None
    ) -> dict:
        """
        智能搜索：先尝试地理编码，然后周边搜索

        Args:
            location_name: 地点名称
            city: 城市

        Returns:
            包含地点信息和周边POI的完整数据
        """
        result = {}

        # 1. 地理编码获取坐标
        try:
            geo_data = self.geocode(location_name, city)
            if geo_data.get("geocodes"):
                geocode = geo_data["geocodes"][0]
                result["location"] = {
                    "coordinate": geocode.get("location"),  # "经度,纬度"
                    "formatted_address": geocode.get("formatted_address"),
                    "province": geocode.get("province"),
                    "city": geocode.get("city"),
                    "district": geocode.get("district")
                }

                # 2. 使用坐标进行周边搜索
                if geocode.get("location"):
                    nearby_data = self.search_nearby(
                        location=geocode["location"],
                        radius=3000,
                        types="|".join(self.get_poi_types()[:10])  # 前10个类型
                    )
                    result["nearby_pois"] = nearby_data.get("pois", [])
        except Exception as e:
            result["error"] = str(e)

        return result


# 全局服务实例
_amap_service_instance: Optional[AmapService] = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例（单例模式）"""
    global _amap_service_instance
    if _amap_service_instance is None:
        _amap_service_instance = AmapService()
    return _amap_service_instance