from __future__ import annotations

from typing import Literal

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
