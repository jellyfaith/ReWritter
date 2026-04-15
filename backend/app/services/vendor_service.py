from __future__ import annotations

import time
from typing import Any

from app.core.settings import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    EMBEDDING_MODEL,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_EMBEDDING_MODEL,
)
from app.repositories import vendor_repository


def ensure_storage() -> None:
    vendor_repository.ensure_vendor_indexes()


def _mask_key(key: str) -> str:
    normalized = (key or "").strip()
    if not normalized:
        return ""
    if len(normalized) <= 8:
        return "*" * len(normalized)
    return f"{normalized[:4]}{'*' * (len(normalized) - 8)}{normalized[-4:]}"


def _fallback_config(capability: str) -> dict[str, Any]:
    if capability == "chat":
        key = DEEPSEEK_API_KEY
        return {
            "vendor_id": "deepseek",
            "display_name": "DeepSeek",
            "api_base": DEEPSEEK_BASE_URL,
            "model": DEEPSEEK_DEFAULT_MODEL,
            "enabled": True,
            "api_key": key,
            "key_configured": bool(key),
            "api_key_mask": _mask_key(key),
            "source": "env",
            "updated_at": int(time.time()),
        }

    key = SILICONFLOW_API_KEY
    return {
        "vendor_id": "siliconflow",
        "display_name": "硅基流动",
        "api_base": SILICONFLOW_BASE_URL,
        "model": SILICONFLOW_EMBEDDING_MODEL or EMBEDDING_MODEL,
        "enabled": True,
        "api_key": key,
        "key_configured": bool(key),
        "api_key_mask": _mask_key(key),
        "source": "env",
        "updated_at": int(time.time()),
    }


def _normalize_stored_config(doc: dict[str, Any]) -> dict[str, Any]:
    key = str(doc.get("api_key", "")).strip()
    return {
        "vendor_id": str(doc.get("vendor_id", "")).strip() or "unknown",
        "display_name": str(doc.get("display_name", "")).strip() or "Unknown",
        "api_base": str(doc.get("api_base", "")).strip(),
        "model": str(doc.get("model", "")).strip(),
        "enabled": bool(doc.get("enabled", True)),
        "api_key": key,
        "key_configured": bool(key),
        "api_key_mask": _mask_key(key),
        "source": "ui",
        "updated_at": int(doc.get("updated_at", 0)),
    }


def get_display_configs(username: str) -> list[dict[str, Any]]:
    stored = vendor_repository.list_configs(username)
    indexed = {str(item.get("capability", "")).strip(): item for item in stored}
    result: list[dict[str, Any]] = []
    for capability in ("chat", "embedding"):
        if capability in indexed:
            merged = _normalize_stored_config(indexed[capability])
        else:
            merged = _fallback_config(capability)
        merged["capability"] = capability
        result.append(merged)
    return result


def save_config(
    username: str,
    capability: str,
    vendor_id: str,
    display_name: str,
    api_base: str,
    api_key: str,
    model: str,
    enabled: bool,
) -> dict[str, Any]:
    normalized_capability = capability.strip().lower()
    if normalized_capability not in {"chat", "embedding"}:
        raise ValueError("capability 不支持")

    payload = {
        "vendor_id": vendor_id.strip(),
        "display_name": display_name.strip(),
        "api_base": api_base.strip(),
        "api_key": api_key.strip(),
        "model": model.strip(),
        "enabled": enabled,
        "updated_at": int(time.time()),
    }
    saved = vendor_repository.upsert_config(username, normalized_capability, payload)
    view = _normalize_stored_config(saved)
    view["capability"] = normalized_capability
    return view


def resolve_chat_vendor(username: str) -> dict[str, Any]:
    doc = vendor_repository.get_config(username, "chat")
    if doc:
        view = _normalize_stored_config(doc)
        if view["enabled"] and view["api_key"]:
            return view
    fallback = _fallback_config("chat")
    return fallback


def resolve_embedding_vendor(username: str) -> dict[str, Any]:
    doc = vendor_repository.get_config(username, "embedding")
    if doc:
        view = _normalize_stored_config(doc)
        if view["enabled"] and view["api_key"]:
            return view
    return _fallback_config("embedding")
