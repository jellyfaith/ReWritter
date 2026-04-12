from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class AgentState(TypedDict, total=False):
    topic: str
    requirements: str
    facts: list[str]
    style_snippets: list[str]
    draft_markdown: str
    status: str


async def search_node(state: AgentState) -> AgentState:
    """联网搜索节点：后续可替换为真实搜索引擎 API。"""
    topic = state.get("topic", "")
    state["facts"] = [
        f"{topic} 相关事实占位符 1",
        f"{topic} 相关事实占位符 2",
    ]
    state["status"] = "searching_done"
    return state


async def rag_style_node(state: AgentState) -> AgentState:
    """RAG 风格检索节点：后续接入 Milvus 相似语料检索。"""
    topic = state.get("topic", "")
    state["style_snippets"] = [
        f"{topic} 风格片段占位符 A",
        f"{topic} 风格片段占位符 B",
    ]
    state["status"] = "style_ready"
    return state


async def generate_node(state: AgentState) -> AgentState:
    """生成节点：后续用 DeepSeek-V2 结合事实和风格生成草稿。"""
    facts = "\n".join(state.get("facts", []))
    styles = "\n".join(state.get("style_snippets", []))

    state["draft_markdown"] = (
        "# 自动生成草稿（占位）\n\n"
        f"## 主题\n{state.get('topic', '')}\n\n"
        f"## 事实依据\n{facts}\n\n"
        f"## 风格参考\n{styles}\n"
    )
    state["status"] = "draft_ready"
    return state


def build_article_graph() -> Any:
    """构建包含 context 流转的 LangGraph 状态图。"""
    graph = StateGraph(AgentState)

    graph.add_node("Search_Node", search_node)
    graph.add_node("RAG_Style_Node", rag_style_node)
    graph.add_node("Generate_Node", generate_node)

    graph.add_edge(START, "Search_Node")
    graph.add_edge("Search_Node", "RAG_Style_Node")
    graph.add_edge("RAG_Style_Node", "Generate_Node")
    graph.add_edge("Generate_Node", END)

    return graph.compile()


async def run_article_workflow(initial_state: AgentState) -> AgentState:
    """运行完整工作流，供 Celery 任务调用。"""
    app = build_article_graph()
    result = await app.ainvoke(initial_state)
    return result
