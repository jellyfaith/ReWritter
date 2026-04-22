from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    topic: str = Field(min_length=1, description="文章主题")
    requirements: str = Field(default="", description="额外写作要求")


class PublishTaskRequest(BaseModel):
    article_markdown: str = Field(min_length=1, description="审核后的文章正文")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict[str, str]


class ChatSessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class ChatSessionUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ChatSessionItem(BaseModel):
    session_id: str
    title: str
    model: str
    enable_thinking: bool
    updated_at: int
    created_at: int


class ChatMessageItem(BaseModel):
    message_id: str
    role: str
    content: str
    thinking_content: str | None = None
    thinking_duration_ms: int | None = None
    model: str | None = None
    enable_thinking: bool | None = None
    created_at: int


class ChatSendRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    model: str = Field(default="deepseek-chat", min_length=1, max_length=80)
    enable_thinking: bool = False
    use_rag: bool = False
    rag_group_id: str | None = Field(default=None, max_length=64)
    rag_top_k: int = Field(default=6, ge=1, le=20)
    rag_search_type: Literal["vector", "hybrid", "keyword"] = "vector"
    rag_alpha: float = Field(default=0.6, ge=0.0, le=1.0)
    rag_candidate_pool: int = Field(default=12, ge=1, le=100)


class ChatSendResponse(BaseModel):
    session: ChatSessionItem
    user_message: ChatMessageItem
    assistant_message: ChatMessageItem


class DeepSeekVendorTestRequest(BaseModel):
    model: str = Field(default="deepseek-chat", min_length=1, max_length=80)
    enable_thinking: bool = False


class DeepSeekVendorTestResponse(BaseModel):
    ok: bool
    vendor: str = "deepseek"
    model: str
    configured: bool
    latency_ms: int | None = None
    message: str


class VendorConfigUpdateRequest(BaseModel):
    capability: Literal["chat", "embedding"]
    vendor_id: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=80)
    api_base: str = Field(min_length=1, max_length=240)
    api_key: str = Field(default="", max_length=240)
    model: str = Field(min_length=1, max_length=120)
    enabled: bool = True


class VendorConfigItem(BaseModel):
    capability: Literal["chat", "embedding"]
    vendor_id: str
    display_name: str
    api_base: str
    model: str
    enabled: bool
    key_configured: bool
    api_key_mask: str
    source: Literal["ui", "env"]
    updated_at: int


class EmbeddingVendorTestResponse(BaseModel):
    ok: bool
    vendor: str
    model: str
    configured: bool
    latency_ms: int | None = None
    message: str


class MaterialGroupItem(BaseModel):
    group_id: str
    group_name: str
    topic: str
    file_count: int
    chunk_count: int
    created_at: int
    updated_at: int


class MaterialFileItem(BaseModel):
    file_id: str
    group_id: str
    file_name: str
    file_size: int
    chunk_count: int
    created_at: int


class MaterialUploadResponse(BaseModel):
    group: MaterialGroupItem
    file: MaterialFileItem
    embedding_provider: str
    message: str


class MaterialRetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    group_id: str | None = Field(default=None, max_length=64)
    top_k: int = Field(default=6, ge=1, le=20)


class MaterialRetrieveItem(BaseModel):
    chunk_id: str
    group_id: str
    group_name: str
    file_id: str
    file_name: str
    chunk_index: int
    content: str
    score: float


class MaterialRetrieveResponse(BaseModel):
    items: list[MaterialRetrieveItem]


class SevenStepCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500, description="选题")
    preferences: str = Field(default="", max_length=2000, description="写作偏好")
    style: str = Field(default="", max_length=80, description="风格")


class SevenStepConfirmTitleRequest(BaseModel):
    main_title: str = Field(min_length=1, max_length=200)
    sub_title: str = Field(default="", max_length=200)


class SevenStepOutlineSection(BaseModel):
    section: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    points: list[str] = Field(default_factory=list)


class SevenStepConfirmOutlineRequest(BaseModel):
    outline: list[SevenStepOutlineSection] = Field(min_length=1)


class SevenStepTitleOption(BaseModel):
    main_title: str
    sub_title: str


class SevenStepImagePlanItem(BaseModel):
    placeholder_id: str
    section_title: str
    description: str
    keywords: str
    status: str = "planned"


class SevenStepAgentTrace(BaseModel):
    agent_id: str
    agent_name: str
    stage: int = Field(ge=1)
    status: str = "completed"
    summary: str
    started_at: int
    finished_at: int


class SevenStepFlowItem(BaseModel):
    flow_id: str
    topic: str
    preferences: str
    style: str
    status: str
    current_step: int
    title_options: list[SevenStepTitleOption] = Field(default_factory=list)
    selected_title: SevenStepTitleOption | None = None
    outline: list[SevenStepOutlineSection] = Field(default_factory=list)
    content: str = ""
    image_plan: list[SevenStepImagePlanItem] = Field(default_factory=list)
    final_markdown: str = ""
    agent_traces: list[SevenStepAgentTrace] = Field(default_factory=list)
    created_at: int
    updated_at: int


# ==================== 用户偏好模型 ====================
class UserPreferences(BaseModel):
    theme: Literal["light", "dark"] = "dark"
    locale: Literal["zh", "en"] = "zh"
    notifications_enabled: bool = True
    default_model: str = "deepseek-chat"
    rag_settings: dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class UserPreferencesUpdateRequest(BaseModel):
    theme: Literal["light", "dark"] | None = None
    locale: Literal["zh", "en"] | None = None
    notifications_enabled: bool | None = None
    default_model: str | None = None
    rag_settings: dict[str, Any] | None = None


class UserPreferencesResponse(BaseModel):
    preferences: UserPreferences


# ==================== 文章管理模型 ====================
class ArticleMetadata(BaseModel):
    word_count: int = 0
    read_time: str = ""
    tags: list[str] = Field(default_factory=list)
    location_info: dict[str, Any] = Field(default_factory=dict)
    author: str = ""
    source: str = ""


class ArticleItem(BaseModel):
    article_id: str
    user_id: str
    title: str
    content_markdown: str
    status: Literal["draft", "published", "archived"] = "draft"
    version: int = 1
    metadata: ArticleMetadata = Field(default_factory=ArticleMetadata)
    created_at: int
    updated_at: int


class ArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content_markdown: str = Field(min_length=1)
    status: Literal["draft", "published", "archived"] = "draft"
    metadata: ArticleMetadata | None = None


class ArticleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_markdown: str | None = Field(default=None, min_length=1)
    status: Literal["draft", "published", "archived"] | None = None
    metadata: ArticleMetadata | None = None


class ArticleVersionItem(BaseModel):
    version_id: str
    article_id: str
    content_markdown: str
    version: int
    created_at: int


class ArticleListResponse(BaseModel):
    articles: list[ArticleItem]
    total: int
    page: int
    page_size: int


class ArticleDownloadRequest(BaseModel):
    format: Literal["markdown", "html", "pdf"] = "markdown"


# ==================== 统计模型 ====================
class DailyStats(BaseModel):
    date: str  # YYYY-MM-DD
    chat_count: int = 0
    creation_count: int = 0
    published_count: int = 0
    updated_at: int


class UserStatsSummary(BaseModel):
    user_id: str
    today_chat_count: int = 0
    total_chat_count: int = 0
    today_creation_count: int = 0
    total_creation_count: int = 0
    today_published_count: int = 0
    total_published_count: int = 0
    active_tasks: int = 0
    updated_at: int


class SystemStats(BaseModel):
    total_users: int = 0
    total_articles: int = 0
    total_chats: int = 0
    active_sessions: int = 0
    system_health: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    updated_at: int


# ==================== 高德地图模型 ====================
class AmapSearchRequest(BaseModel):
    keywords: str = Field(min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=50)
    city_limit: bool = True
    page_size: int = Field(default=20, ge=1, le=50)
    page_num: int = Field(default=1, ge=1)


class AmapPoiItem(BaseModel):
    id: str
    name: str
    type: str
    address: str
    location: str  # "经度,纬度"
    distance: str | None = None
    tel: str | None = None
    rating: str | None = None


class AmapSearchResponse(BaseModel):
    pois: list[AmapPoiItem]
    total: int
    page: int
    page_size: int


class AmapNearbyRequest(BaseModel):
    location: str = Field(min_length=1, max_length=50)  # "经度,纬度"
    radius: int = Field(default=3000, ge=100, le=50000)
    types: str | None = Field(default=None, max_length=200)
    page_size: int = Field(default=20, ge=1, le=50)
    page_num: int = Field(default=1, ge=1)


class AmapGeocodeRequest(BaseModel):
    address: str = Field(min_length=1, max_length=200)
    city: str | None = Field(default=None, max_length=50)


class AmapGeocodeResponse(BaseModel):
    location: str  # "经度,纬度"
    formatted_address: str
    country: str
    province: str
    city: str
    district: str
    township: str | None = None


# ==================== 发布模型 ====================
class PublishTaskRequest(BaseModel):
    article_id: str
    platform: Literal["xiaohongshu", "zhihu", "wechat"] = "xiaohongshu"
    schedule_time: int | None = None  # Unix timestamp
    options: dict[str, Any] = Field(default_factory=dict)


class PublishStatusItem(BaseModel):
    task_id: str
    article_id: str
    platform: str
    status: Literal["pending", "processing", "published", "failed"]
    message: str | None = None
    published_url: str | None = None
    created_at: int
    updated_at: int


class PublishHistoryResponse(BaseModel):
    items: list[PublishStatusItem]
    total: int
    page: int
    page_size: int
