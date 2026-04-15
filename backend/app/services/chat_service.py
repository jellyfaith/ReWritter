from __future__ import annotations

import secrets
import time
from typing import Any, Generator

from fastapi import HTTPException, status
from openai import OpenAI

from app.core.settings import (
    DEEPSEEK_DEFAULT_MODEL,
    DEEPSEEK_REASONER_MODEL,
)
from app.repositories import chat_repository
from app.schemas import ChatMessageItem, ChatSessionItem
from app.services import material_service, vendor_service
from app.services.chat_utils import (
    build_prompt_messages,
    normalize_session_title,
    resolve_model,
    sse_payload,
    to_text_piece,
)


def ensure_storage() -> None:
    chat_repository.ensure_chat_indexes()


def serialize_session(doc: dict[str, Any]) -> ChatSessionItem:
    return ChatSessionItem(
        session_id=str(doc.get("session_id", "")),
        title=str(doc.get("title", "新对话")),
        model=str(doc.get("model", DEEPSEEK_DEFAULT_MODEL)),
        enable_thinking=bool(doc.get("enable_thinking", False)),
        updated_at=int(doc.get("updated_at", 0)),
        created_at=int(doc.get("created_at", 0)),
    )


def serialize_message(doc: dict[str, Any]) -> ChatMessageItem:
    thinking_duration_ms = doc.get("thinking_duration_ms")
    return ChatMessageItem(
        message_id=str(doc.get("message_id", "")),
        role=str(doc.get("role", "assistant")),
        content=str(doc.get("content", "")),
        thinking_content=str(doc.get("thinking_content", "")) or None,
        thinking_duration_ms=int(thinking_duration_ms) if thinking_duration_ms is not None else None,
        model=str(doc.get("model")) if doc.get("model") is not None else None,
        enable_thinking=bool(doc.get("enable_thinking")) if doc.get("enable_thinking") is not None else None,
        created_at=int(doc.get("created_at", 0)),
    )


def create_session(username: str, title: str | None, model: str, enable_thinking: bool) -> dict[str, Any]:
    now = int(time.time())
    session_doc = {
        "session_id": f"chat_{secrets.token_hex(8)}",
        "username": username,
        "title": normalize_session_title(title),
        "model": model,
        "enable_thinking": enable_thinking,
        "created_at": now,
        "updated_at": now,
    }
    chat_repository.create_session(session_doc)
    return session_doc


def list_sessions(username: str) -> list[dict[str, Any]]:
    return chat_repository.list_sessions(username)


def list_messages(session_id: str) -> list[dict[str, Any]]:
    return chat_repository.list_messages(session_id)


def rename_session(session_id: str, username: str, title: str) -> dict[str, Any] | None:
    return chat_repository.rename_session(session_id, username, normalize_session_title(title), int(time.time()))


def delete_session(session_id: str, username: str) -> bool:
    return chat_repository.delete_session(session_id, username)


def get_session(session_id: str, username: str) -> dict[str, Any] | None:
    return chat_repository.get_session(session_id, username)


def _ensure_llm_ready(username: str) -> dict[str, Any]:
    resolved = vendor_service.resolve_chat_vendor(username)
    if not str(resolved.get("api_key", "")).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置 DEEPSEEK_API_KEY，无法调用聊天模型",
        )
    return resolved


def run_llm_chat(messages: list[dict[str, str]], model: str, enable_thinking: bool, username: str) -> tuple[str, str]:
    resolved_vendor = _ensure_llm_ready(username)
    resolved_model = resolve_model(model, enable_thinking, DEEPSEEK_DEFAULT_MODEL, DEEPSEEK_REASONER_MODEL)
    client = OpenAI(
        api_key=str(resolved_vendor.get("api_key", "")).strip(),
        base_url=str(resolved_vendor.get("api_base", "")).strip(),
    )
    try:
        response = client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=0.6,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"模型服务调用失败: {exc}") from exc

    choice = response.choices[0] if response.choices else None
    content = ""
    if choice and getattr(choice, "message", None) is not None:
        content = str(choice.message.content or "").strip()

    if not content:
        raise HTTPException(status_code=502, detail="模型返回为空，请稍后重试")

    return content, resolved_model


def build_prompt_from_session(session_id: str) -> list[dict[str, str]]:
    return build_prompt_messages(chat_repository.list_prompt_messages(session_id))


def build_prompt_with_rag(
    session_id: str,
    username: str,
    user_input: str,
    use_rag: bool,
    rag_group_id: str | None,
    rag_top_k: int,
) -> list[dict[str, str]]:
    prompt_messages = build_prompt_from_session(session_id)
    if not use_rag:
        return prompt_messages

    context_text, _ = material_service.build_rag_context(
        username=username,
        query=user_input,
        group_id=rag_group_id,
        top_k=rag_top_k,
    )
    if not context_text:
        return prompt_messages

    rag_system_message = (
        "你正在基于用户提供的素材库回答问题。"
        "请优先依据以下素材片段作答，若素材不足请明确说明，并给出你能确认的结论。"
        "\n\n[素材片段开始]\n"
        f"{context_text}\n"
        "[素材片段结束]"
    )
    return [{"role": "system", "content": rag_system_message}, *prompt_messages]


def save_user_message(session_id: str, content: str) -> dict[str, Any]:
    doc = {
        "message_id": f"msg_{secrets.token_hex(8)}",
        "session_id": session_id,
        "role": "user",
        "content": content.strip(),
        "created_at": int(time.time()),
    }
    chat_repository.insert_message(doc)
    return doc


def save_assistant_message(
    session_id: str,
    content: str,
    thinking_content: str,
    model: str,
    enable_thinking: bool,
    thinking_duration_ms: int | None = None,
) -> dict[str, Any]:
    doc = {
        "message_id": f"msg_{secrets.token_hex(8)}",
        "session_id": session_id,
        "role": "assistant",
        "content": content,
        "thinking_content": thinking_content,
        "thinking_duration_ms": thinking_duration_ms,
        "model": model,
        "enable_thinking": enable_thinking,
        "created_at": int(time.time()),
    }
    chat_repository.insert_message(doc)
    return doc


def touch_session(session_doc: dict[str, Any], username: str, model: str, enable_thinking: bool, user_input: str) -> dict[str, Any] | None:
    latest_title = str(session_doc.get("title", "新对话"))
    if latest_title == "新对话":
        latest_title = user_input.strip()[:24] or "新对话"
    return chat_repository.touch_session(
        session_id=str(session_doc.get("session_id", "")),
        username=username,
        title=latest_title,
        model=model,
        enable_thinking=enable_thinking,
        updated_at=int(time.time()),
    )


def stream_llm_events(
    session_doc: dict[str, Any],
    username: str,
    session_id: str,
    user_input: str,
    model: str,
    enable_thinking: bool,
    use_rag: bool,
    rag_group_id: str | None,
    rag_top_k: int,
) -> Generator[str, None, None]:
    stream_started_at = time.perf_counter()
    assistant_content_parts: list[str] = []
    thinking_content_parts: list[str] = []

    save_user_message(session_id, user_input)
    prompt_messages = build_prompt_with_rag(
        session_id=session_id,
        username=username,
        user_input=user_input,
        use_rag=use_rag,
        rag_group_id=rag_group_id,
        rag_top_k=rag_top_k,
    )

    try:
        resolved_vendor = _ensure_llm_ready(username)
        resolved_model = resolve_model(model, enable_thinking, DEEPSEEK_DEFAULT_MODEL, DEEPSEEK_REASONER_MODEL)
        client = OpenAI(
            api_key=str(resolved_vendor.get("api_key", "")).strip(),
            base_url=str(resolved_vendor.get("api_base", "")).strip(),
        )
        stream = client.chat.completions.create(
            model=resolved_model,
            messages=prompt_messages,
            temperature=0.6,
            stream=True,
        )
    except HTTPException as exc:
        yield sse_payload({"type": "error", "message": str(exc.detail)})
        return
    except Exception as exc:
        yield sse_payload({"type": "error", "message": f"模型服务调用失败: {exc}"})
        return

    try:
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue

            thinking_delta = to_text_piece(getattr(delta, "reasoning_content", None))
            if not thinking_delta:
                thinking_delta = to_text_piece(getattr(delta, "reasoning", None))
            if thinking_delta:
                thinking_content_parts.append(thinking_delta)
                yield sse_payload({"type": "thinking_delta", "delta": thinking_delta})

            content_delta = to_text_piece(getattr(delta, "content", None))
            if not content_delta:
                content_delta = to_text_piece(getattr(delta, "output_text", None))
            if content_delta:
                assistant_content_parts.append(content_delta)
                yield sse_payload({"type": "content_delta", "delta": content_delta})
    except Exception as exc:
        yield sse_payload({"type": "error", "message": f"流式响应中断: {exc}"})
        return

    assistant_content = "".join(assistant_content_parts).strip()
    thinking_content = "".join(thinking_content_parts).strip()
    if not assistant_content:
        yield sse_payload({"type": "error", "message": "模型返回为空，请稍后重试"})
        return

    thinking_duration_ms = int((time.perf_counter() - stream_started_at) * 1000) if enable_thinking and thinking_content else None
    assistant_doc = save_assistant_message(
        session_id=session_id,
        content=assistant_content,
        thinking_content=thinking_content,
        thinking_duration_ms=thinking_duration_ms,
        model=resolved_model,
        enable_thinking=enable_thinking,
    )

    updated_session = touch_session(session_doc, username, resolved_model, enable_thinking, user_input)
    if updated_session is None:
        yield sse_payload({"type": "error", "message": "会话更新失败"})
        return

    yield sse_payload(
        {
            "type": "done",
            "session": serialize_session(updated_session).model_dump(),
            "assistant_message": serialize_message(assistant_doc).model_dump(),
        }
    )
