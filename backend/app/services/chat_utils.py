from __future__ import annotations

import json
from typing import Any


def normalize_session_title(raw_title: str | None) -> str:
    title = (raw_title or "").strip()
    if not title:
        return "新对话"
    return title[:120]


def resolve_model(model: str, enable_thinking: bool, default_model: str, reasoner_model: str) -> str:
    normalized = model.strip() or default_model
    if enable_thinking and normalized == default_model:
        return reasoner_model
    return normalized


def to_text_piece(raw_piece: Any) -> str:
    if raw_piece is None:
        return ""
    if isinstance(raw_piece, str):
        return raw_piece
    if isinstance(raw_piece, list):
        parts: list[str] = []
        for item in raw_piece:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                text_value = getattr(item, "text", None)
                if text_value is not None:
                    parts.append(str(text_value))
        return "".join(parts)
    return str(raw_piece)


def sse_payload(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_prompt_messages(message_docs: list[dict[str, Any]]) -> list[dict[str, str]]:
    prompt_messages: list[dict[str, str]] = []
    for doc in message_docs:
        content = str(doc.get("content", "")).strip()
        if not content:
            continue
        prompt_messages.append({
            "role": str(doc.get("role", "assistant")),
            "content": content,
        })
    return prompt_messages
