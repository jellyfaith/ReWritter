from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import require_auth
from app.schemas import (
    ChatMessageItem,
    ChatSendRequest,
    ChatSendResponse,
    ChatSessionCreateRequest,
    ChatSessionItem,
    ChatSessionUpdateRequest,
)
from app.services import chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions", response_model=list[ChatSessionItem])
async def list_chat_sessions(
    _auth: dict[str, Any] = Depends(require_auth),
) -> list[ChatSessionItem]:
    username = str(_auth.get("sub", "")).strip()
    return [chat_service.serialize_session(doc) for doc in chat_service.list_sessions(username)]


@router.post("/sessions", response_model=ChatSessionItem)
async def create_chat_session(
    payload: ChatSessionCreateRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> ChatSessionItem:
    username = str(_auth.get("sub", "")).strip()
    doc = chat_service.create_session(username, payload.title, model="deepseek-chat", enable_thinking=False)
    return chat_service.serialize_session(doc)


@router.patch("/sessions/{session_id}", response_model=ChatSessionItem)
async def rename_chat_session(
    session_id: str,
    payload: ChatSessionUpdateRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> ChatSessionItem:
    username = str(_auth.get("sub", "")).strip()
    updated = chat_service.rename_session(session_id, username, payload.title)
    if updated is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return chat_service.serialize_session(updated)


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    _auth: dict[str, Any] = Depends(require_auth),
) -> dict[str, str]:
    username = str(_auth.get("sub", "")).strip()
    ok = chat_service.delete_session(session_id, username)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"status": "deleted", "session_id": session_id}


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageItem])
async def list_chat_messages(
    session_id: str,
    _auth: dict[str, Any] = Depends(require_auth),
) -> list[ChatMessageItem]:
    username = str(_auth.get("sub", "")).strip()
    session_doc = chat_service.get_session(session_id, username)
    if not session_doc:
        raise HTTPException(status_code=404, detail="会话不存在")
    return [chat_service.serialize_message(doc) for doc in chat_service.list_messages(session_id)]


@router.post("/sessions/{session_id}/messages", response_model=ChatSendResponse)
async def send_chat_message(
    session_id: str,
    payload: ChatSendRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> ChatSendResponse:
    username = str(_auth.get("sub", "")).strip()
    session_doc = chat_service.get_session(session_id, username)
    if not session_doc:
        raise HTTPException(status_code=404, detail="会话不存在")

    user_doc = chat_service.save_user_message(session_id, payload.content)
    prompt_messages = chat_service.build_prompt_with_rag(
        session_id=session_id,
        username=username,
        user_input=payload.content,
        use_rag=payload.use_rag,
        rag_group_id=payload.rag_group_id,
        rag_top_k=payload.rag_top_k,
    )
    assistant_content, resolved_model = chat_service.run_llm_chat(
        prompt_messages,
        payload.model,
        payload.enable_thinking,
        username,
    )
    assistant_doc = chat_service.save_assistant_message(
        session_id=session_id,
        content=assistant_content,
        thinking_content="",
        model=resolved_model,
        enable_thinking=payload.enable_thinking,
    )

    updated_session = chat_service.touch_session(session_doc, username, resolved_model, payload.enable_thinking, payload.content)
    if updated_session is None:
        raise HTTPException(status_code=500, detail="会话更新失败")

    return ChatSendResponse(
        session=chat_service.serialize_session(updated_session),
        user_message=chat_service.serialize_message(user_doc),
        assistant_message=chat_service.serialize_message(assistant_doc),
    )


@router.post("/sessions/{session_id}/messages/stream")
async def stream_chat_message(
    session_id: str,
    payload: ChatSendRequest,
    _auth: dict[str, Any] = Depends(require_auth),
) -> StreamingResponse:
    username = str(_auth.get("sub", "")).strip()
    session_doc = chat_service.get_session(session_id, username)
    if not session_doc:
        raise HTTPException(status_code=404, detail="会话不存在")

    return StreamingResponse(
        chat_service.stream_llm_events(
            session_doc=session_doc,
            username=username,
            session_id=session_id,
            user_input=payload.content,
            model=payload.model,
            enable_thinking=payload.enable_thinking,
            use_rag=payload.use_rag,
            rag_group_id=payload.rag_group_id,
            rag_top_k=payload.rag_top_k,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
