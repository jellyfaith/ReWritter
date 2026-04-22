from __future__ import annotations

import json
import re
import secrets
import time
from typing import Any

from fastapi import HTTPException, status

from app.core.settings import DEEPSEEK_DEFAULT_MODEL
from app.repositories import writing_flow_repository
from app.schemas import (
    SevenStepAgentTrace,
    SevenStepFlowItem,
    SevenStepImagePlanItem,
    SevenStepOutlineSection,
    SevenStepTitleOption,
)
from app.services import chat_service
from app.services.writing_image_planner import ImagePlanProvider, PlaceholderImagePlanProvider

_STATUS_TITLES_READY = "TITLES_READY"
_STATUS_OUTLINE_READY = "OUTLINE_READY"
_STATUS_COMPLETED = "COMPLETED"


_image_plan_provider: ImagePlanProvider = PlaceholderImagePlanProvider()


def ensure_storage() -> None:
    writing_flow_repository.ensure_writing_flow_indexes()


def serialize_flow(doc: dict[str, Any]) -> SevenStepFlowItem:
    return SevenStepFlowItem(
        flow_id=str(doc.get("flow_id", "")),
        topic=str(doc.get("topic", "")),
        preferences=str(doc.get("preferences", "")),
        style=str(doc.get("style", "")),
        status=str(doc.get("status", _STATUS_TITLES_READY)),
        current_step=int(doc.get("current_step", 1)),
        title_options=[SevenStepTitleOption(**item) for item in doc.get("title_options", [])],
        selected_title=SevenStepTitleOption(**doc["selected_title"]) if doc.get("selected_title") else None,
        outline=[SevenStepOutlineSection(**item) for item in doc.get("outline", [])],
        content=str(doc.get("content", "")),
        image_plan=[SevenStepImagePlanItem(**item) for item in doc.get("image_plan", [])],
        final_markdown=str(doc.get("final_markdown", "")),
        agent_traces=[SevenStepAgentTrace(**item) for item in doc.get("agent_traces", [])],
        created_at=int(doc.get("created_at", 0)),
        updated_at=int(doc.get("updated_at", 0)),
    )


def _build_agent_trace(
    agent_id: str,
    agent_name: str,
    stage: int,
    summary: str,
    started_at: int,
    finished_at: int,
    status_text: str = "completed",
) -> SevenStepAgentTrace:
    return SevenStepAgentTrace(
        agent_id=agent_id,
        agent_name=agent_name,
        stage=stage,
        status=status_text,
        summary=summary,
        started_at=started_at,
        finished_at=finished_at,
    )


def _append_agent_traces(doc: dict[str, Any], traces: list[SevenStepAgentTrace]) -> list[dict[str, Any]]:
    history = list(doc.get("agent_traces", []))
    history.extend(trace.model_dump() for trace in traces)
    return history


def _sanitize_outline(outline: list[SevenStepOutlineSection]) -> list[SevenStepOutlineSection]:
    sanitized: list[SevenStepOutlineSection] = []
    for idx, section in enumerate(outline, start=1):
        title = section.title.strip()
        if not title:
            continue
        points = [point.strip() for point in section.points if point.strip()]
        if len(points) < 2:
            points = points + ["补充关键判断标准", "补充落地执行建议"]
        sanitized.append(
            SevenStepOutlineSection(
                section=idx,
                title=title,
                points=points[:4],
            )
        )
    return sanitized[:6]


def _run_outline_agents(
    username: str,
    topic: str,
    preferences: str,
    style: str,
    selected_title: SevenStepTitleOption,
) -> tuple[list[SevenStepOutlineSection], list[SevenStepAgentTrace]]:
    traces: list[SevenStepAgentTrace] = []

    start_outline = int(time.time())
    outline = _generate_outline(username, topic, preferences, style, selected_title)
    end_outline = int(time.time())
    traces.append(
        _build_agent_trace(
            agent_id="agent2_outline_planner",
            agent_name="Agent-2 大纲生成",
            stage=4,
            summary=f"输出 {len(outline)} 个章节草案",
            started_at=start_outline,
            finished_at=end_outline,
        )
    )

    start_refine = int(time.time())
    refined_outline = _sanitize_outline(outline)
    end_refine = int(time.time())
    traces.append(
        _build_agent_trace(
            agent_id="agent2_outline_refiner",
            agent_name="Agent-2R 大纲质检",
            stage=4,
            summary=f"完成结构规整，保留 {len(refined_outline)} 个章节",
            started_at=start_refine,
            finished_at=end_refine,
        )
    )

    return refined_outline, traces


def _run_delivery_agents(
    username: str,
    topic: str,
    preferences: str,
    style: str,
    selected_title: SevenStepTitleOption,
    outline: list[SevenStepOutlineSection],
) -> tuple[str, list[SevenStepImagePlanItem], str, list[SevenStepAgentTrace]]:
    traces: list[SevenStepAgentTrace] = []

    start_content = int(time.time())
    content = _generate_content(username, topic, preferences, style, selected_title, outline)
    end_content = int(time.time())
    traces.append(
        _build_agent_trace(
            agent_id="agent3_content_writer",
            agent_name="Agent-3 正文生成",
            stage=6,
            summary=f"生成正文 {len(content)} 字符",
            started_at=start_content,
            finished_at=end_content,
        )
    )

    start_image = int(time.time())
    image_plan = _image_plan_provider.plan(topic=topic, outline=outline, content=content)
    end_image = int(time.time())
    traces.append(
        _build_agent_trace(
            agent_id="agent4_image_planner",
            agent_name="Agent-4 配图规划",
            stage=6,
            summary=f"规划 {len(image_plan)} 个占位图",
            started_at=start_image,
            finished_at=end_image,
        )
    )

    start_merge = int(time.time())
    final_markdown = _merge_content_with_image_placeholders(content, image_plan)
    end_merge = int(time.time())
    traces.append(
        _build_agent_trace(
            agent_id="agent5_content_merger",
            agent_name="Agent-5 图文合成",
            stage=7,
            summary=f"输出成品 {len(final_markdown)} 字符",
            started_at=start_merge,
            finished_at=end_merge,
        )
    )

    return content, image_plan, final_markdown, traces


def create_flow(username: str, topic: str, preferences: str, style: str) -> SevenStepFlowItem:
    now = int(time.time())
    title_start = int(time.time())
    title_options = _generate_titles(username, topic, preferences, style)
    title_end = int(time.time())
    title_trace = _build_agent_trace(
        agent_id="agent1_title_planner",
        agent_name="Agent-1 标题策划",
        stage=2,
        summary=f"生成 {len(title_options)} 个标题候选",
        started_at=title_start,
        finished_at=title_end,
    )
    doc = {
        "flow_id": f"wf_{secrets.token_hex(8)}",
        "username": username,
        "topic": topic.strip(),
        "preferences": preferences.strip(),
        "style": style.strip(),
        "status": _STATUS_TITLES_READY,
        "current_step": 2,
        "title_options": [item.model_dump() for item in title_options],
        "selected_title": None,
        "outline": [],
        "content": "",
        "image_plan": [],
        "final_markdown": "",
        "agent_traces": [title_trace.model_dump()],
        "created_at": now,
        "updated_at": now,
    }
    writing_flow_repository.create_flow(doc)
    return serialize_flow(doc)


def get_flow(username: str, flow_id: str) -> SevenStepFlowItem:
    doc = writing_flow_repository.get_flow(flow_id, username)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="七步写作会话不存在")
    return serialize_flow(doc)


def confirm_title(username: str, flow_id: str, main_title: str, sub_title: str) -> SevenStepFlowItem:
    doc = writing_flow_repository.get_flow(flow_id, username)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="七步写作会话不存在")
    if str(doc.get("status")) not in {_STATUS_TITLES_READY, _STATUS_OUTLINE_READY}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前阶段不允许确认标题")

    topic = str(doc.get("topic", ""))
    preferences = str(doc.get("preferences", ""))
    style = str(doc.get("style", ""))
    selected_title = SevenStepTitleOption(main_title=main_title.strip(), sub_title=sub_title.strip())
    outline, traces = _run_outline_agents(username, topic, preferences, style, selected_title)

    updated = writing_flow_repository.update_flow(
        flow_id,
        username,
        {
            "selected_title": selected_title.model_dump(),
            "outline": [item.model_dump() for item in outline],
            "agent_traces": _append_agent_traces(doc, traces),
            "status": _STATUS_OUTLINE_READY,
            "current_step": 4,
            "updated_at": int(time.time()),
        },
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新七步写作会话失败")
    return serialize_flow(updated)


def confirm_outline(username: str, flow_id: str, outline: list[SevenStepOutlineSection]) -> SevenStepFlowItem:
    doc = writing_flow_repository.get_flow(flow_id, username)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="七步写作会话不存在")
    if str(doc.get("status")) != _STATUS_OUTLINE_READY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前阶段不允许确认大纲")

    topic = str(doc.get("topic", ""))
    preferences = str(doc.get("preferences", ""))
    style = str(doc.get("style", ""))
    selected_raw = doc.get("selected_title") or {}
    selected_title = SevenStepTitleOption(
        main_title=str(selected_raw.get("main_title", topic)),
        sub_title=str(selected_raw.get("sub_title", "")),
    )
    normalized_outline = _sanitize_outline(outline)
    content, image_plan, final_markdown, traces = _run_delivery_agents(
        username=username,
        topic=topic,
        preferences=preferences,
        style=style,
        selected_title=selected_title,
        outline=normalized_outline,
    )

    updated = writing_flow_repository.update_flow(
        flow_id,
        username,
        {
            "outline": [item.model_dump() for item in normalized_outline],
            "content": content,
            "image_plan": [item.model_dump() for item in image_plan],
            "final_markdown": final_markdown,
            "agent_traces": _append_agent_traces(doc, traces),
            "status": _STATUS_COMPLETED,
            "current_step": 7,
            "updated_at": int(time.time()),
        },
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新七步写作会话失败")
    return serialize_flow(updated)


def _extract_json_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\\n", "", text)
        text = re.sub(r"\\n```$", "", text)
    return text.strip()


def _generate_titles(username: str, topic: str, preferences: str, style: str) -> list[SevenStepTitleOption]:
    prompt = (
        "你是资深中文编辑。基于给定选题和偏好，生成 4 个标题候选。"
        "输出严格 JSON，格式为数组："
        "[{\"main_title\":\"主标题\",\"sub_title\":\"副标题\"}]。"
        "不要输出任何多余文本。"
        f"\n选题：{topic}\n偏好：{preferences or '无'}\n风格：{style or '默认'}"
    )
    try:
        content, _ = chat_service.run_llm_chat(
            messages=[{"role": "user", "content": prompt}],
            model=DEEPSEEK_DEFAULT_MODEL,
            enable_thinking=False,
            username=username,
        )
        data = json.loads(_extract_json_text(content))
        result: list[SevenStepTitleOption] = []
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                main = str(item.get("main_title", "")).strip()
                if not main:
                    continue
                result.append(
                    SevenStepTitleOption(
                        main_title=main,
                        sub_title=str(item.get("sub_title", "")).strip(),
                    )
                )
        if result:
            return result[:5]
    except Exception:
        pass

    return [
        SevenStepTitleOption(main_title=f"{topic}：你真正需要知道的 5 个关键点", sub_title="从误区到实战，一次讲清"),
        SevenStepTitleOption(main_title=f"{topic} 完整指南", sub_title="适合上手与进阶的双层结构"),
        SevenStepTitleOption(main_title=f"用七步拆解 {topic}", sub_title="可执行的写作与表达路径"),
        SevenStepTitleOption(main_title=f"为什么你总写不好 {topic}", sub_title="常见问题与可复用解法"),
    ]


def _generate_outline(
    username: str,
    topic: str,
    preferences: str,
    style: str,
    selected_title: SevenStepTitleOption,
) -> list[SevenStepOutlineSection]:
    prompt = (
        "请为文章生成大纲。输出严格 JSON，格式："
        "[{\"section\":1,\"title\":\"章节名\",\"points\":[\"要点1\",\"要点2\"]}]。"
        "要求 4-6 个章节，每章 2-4 个要点。不要输出其他文本。"
        f"\n选题：{topic}"
        f"\n主标题：{selected_title.main_title}"
        f"\n副标题：{selected_title.sub_title or '无'}"
        f"\n偏好：{preferences or '无'}"
        f"\n风格：{style or '默认'}"
    )
    try:
        content, _ = chat_service.run_llm_chat(
            messages=[{"role": "user", "content": prompt}],
            model=DEEPSEEK_DEFAULT_MODEL,
            enable_thinking=False,
            username=username,
        )
        data = json.loads(_extract_json_text(content))
        outline: list[SevenStepOutlineSection] = []
        if isinstance(data, list):
            for idx, item in enumerate(data, start=1):
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "")).strip()
                if not title:
                    continue
                points_raw = item.get("points", [])
                points = [str(p).strip() for p in points_raw if str(p).strip()] if isinstance(points_raw, list) else []
                if not points:
                    continue
                outline.append(SevenStepOutlineSection(section=idx, title=title, points=points[:4]))
        if outline:
            return outline[:6]
    except Exception:
        pass

    return [
        SevenStepOutlineSection(section=1, title="背景与核心问题", points=["为什么这个主题值得写", "读者最关心的问题是什么"]),
        SevenStepOutlineSection(section=2, title="关键概念拆解", points=["核心概念定义", "常见误区对照"]),
        SevenStepOutlineSection(section=3, title="方法与步骤", points=["可执行步骤", "每一步的注意事项"]),
        SevenStepOutlineSection(section=4, title="案例与落地", points=["典型案例", "可复用模板"]),
        SevenStepOutlineSection(section=5, title="结论与行动建议", points=["重点回顾", "下一步行动清单"]),
    ]


def _generate_content(
    username: str,
    topic: str,
    preferences: str,
    style: str,
    selected_title: SevenStepTitleOption,
    outline: list[SevenStepOutlineSection],
) -> str:
    outline_json = json.dumps([item.model_dump() for item in outline], ensure_ascii=False)
    prompt = (
        "根据给定标题和大纲写一篇中文 Markdown 文章。"
        "结构清晰、段落完整、每个二级标题都要覆盖对应要点。"
        f"\n主标题：{selected_title.main_title}"
        f"\n副标题：{selected_title.sub_title or '无'}"
        f"\n选题：{topic}"
        f"\n偏好：{preferences or '无'}"
        f"\n风格：{style or '默认'}"
        f"\n大纲：{outline_json}"
    )

    try:
        content, _ = chat_service.run_llm_chat(
            messages=[{"role": "user", "content": prompt}],
            model=DEEPSEEK_DEFAULT_MODEL,
            enable_thinking=False,
            username=username,
        )
        normalized = content.strip()
        if normalized:
            return normalized
    except Exception:
        pass

    lines: list[str] = [f"# {selected_title.main_title}"]
    if selected_title.sub_title:
        lines.append(f"> {selected_title.sub_title}")
    lines.append("")
    for section in outline:
        lines.append(f"## {section.section}. {section.title}")
        for point in section.points:
            lines.append(f"- {point}")
        lines.append("")
        lines.append("这里补充与本节相关的核心解释、案例与可执行建议。")
        lines.append("")
    return "\n".join(lines).strip()


def _merge_content_with_image_placeholders(content: str, image_plan: list[SevenStepImagePlanItem]) -> str:
    merged = content.rstrip()
    if not image_plan:
        return merged

    merged += "\n\n---\n\n## 配图占位（待接入图片服务）\n"
    for item in image_plan:
        merged += (
            f"\n- [{item.placeholder_id}] {item.section_title}"
            f"\n  - 描述：{item.description}"
            f"\n  - 关键词：{item.keywords}"
            f"\n  - 占位引用：![{item.section_title}](placeholder://{item.placeholder_id})\n"
        )
    return merged
