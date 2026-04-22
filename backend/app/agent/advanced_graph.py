from __future__ import annotations

import json
import time
from typing import Any, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import SevenStepTitleOption, SevenStepOutlineSection
from app.services.amap_service import get_amap_service
from app.services.rag_service import get_rag_service  # 稍后创建 # noqa: F401


class AdvancedAgentState(TypedDict, total=False):
    """高级Agent工作流状态"""
    # 输入参数
    topic: str
    requirements: str
    style: str
    location: Optional[str]  # 地理位置信息
    user_id: str

    # 步骤1: 地点增强
    location_data: Optional[dict]  # 高德地图返回的地点信息
    nearby_pois: List[dict]  # 周边POI列表

    # 步骤2: 标题策划
    title_options: List[SevenStepTitleOption]
    selected_title: Optional[SevenStepTitleOption]

    # 步骤3: 大纲生成
    outline: List[SevenStepOutlineSection]
    outline_quality_check: bool

    # 步骤4: 正文生成
    content_markdown: str
    content_quality_check: bool

    # 步骤5: 配图规划
    image_plan: List[dict]

    # 步骤6: 图文合成
    final_markdown: str

    # 步骤7: 发布准备
    publish_ready: bool
    publish_platform: str
    publish_schedule: Optional[int]

    # RAG检索结果
    rag_results: List[dict]

    # 工作流状态
    current_step: int
    status: str
    error: Optional[str]
    start_time: float
    end_time: Optional[float]


# ==================== 节点定义 ====================

async def location_enhancement_node(state: AdvancedAgentState) -> AdvancedAgentState:
    """地点增强节点：集成高德地图信息"""
    print(f"步骤1: 地点增强 - 主题: {state.get('topic', '')}")

    try:
        location = state.get("location")
        topic = state.get("topic", "")

        if location:
            # 如果有具体地点，使用高德地图查询
            amap_service = get_amap_service()
            result = amap_service.search_with_fallback(location, city=None)

            state["location_data"] = result.get("location")
            state["nearby_pois"] = result.get("nearby_pois", [])[:10]  # 取前10个POI

            print(f"  地点信息获取成功: {len(state['nearby_pois'])}个周边POI")
        else:
            # 从主题中提取可能的地点关键词
            # 简单实现：检查主题中是否包含常见地点关键词
            location_keywords = ["北京", "上海", "广州", "深圳", "杭州", "成都", "旅游", "景点", "公园", "餐厅"]
            found_locations = [kw for kw in location_keywords if kw in topic]

            if found_locations:
                state["location"] = found_locations[0]
                # 递归调用自身处理找到的地点
                return await location_enhancement_node(state)
            else:
                state["location_data"] = None
                state["nearby_pois"] = []

        state["current_step"] = 1
        state["status"] = "location_enhanced"

    except Exception as e:
        state["error"] = f"地点增强失败: {str(e)}"
        state["status"] = "error"

    return state


async def rag_retrieval_node(state: AdvancedAgentState) -> AdvancedAgentState:
    """RAG检索节点：检索相关素材"""
    print(f"步骤2: RAG检索 - 主题: {state.get('topic', '')}")

    try:
        # 这里暂时使用占位实现，后续集成真实的RAG服务
        # rag_service = get_rag_service()
        # query = f"{state.get('topic', '')} {state.get('requirements', '')}"
        # results = rag_service.hybrid_search(query, top_k=5)

        # 占位实现
        state["rag_results"] = [
            {
                "content": f"关于{state.get('topic', '')}的相关素材1",
                "score": 0.95,
                "source": "素材库"
            },
            {
                "content": f"关于{state.get('topic', '')}的风格参考",
                "score": 0.87,
                "source": "风格库"
            }
        ]

        print(f"  RAG检索完成: {len(state['rag_results'])}个结果")
        state["current_step"] = 2
        state["status"] = "rag_retrieved"

    except Exception as e:
        state["error"] = f"RAG检索失败: {str(e)}"
        state["status"] = "error"

    return state


async def title_planning_node(state: AdvancedAgentState) -> AdvancedAgentState:
    """标题策划节点：生成标题选项"""
    print("步骤3: 标题策划")

    try:
        topic = state.get("topic", "")
        location_data = state.get("location_data")
        nearby_pois = state.get("nearby_pois", [])

        # 构建地点上下文
        location_context = ""
        if location_data:
            city = location_data.get("city", "")
            address = location_data.get("formatted_address", "")
            location_context = f"在{city}{address}附近"

        # 构建POI上下文
        poi_context = ""
        if nearby_pois and len(nearby_pois) > 0:
            poi_names = [poi.get("name", "") for poi in nearby_pois[:3]]
            poi_context = f"，周边有{', '.join(poi_names)}等地点"

        # 生成标题选项（实际应该调用AI模型）
        title_options = []

        # 选项1: 常规标题
        title_options.append(SevenStepTitleOption(
            main_title=f"{topic}的完整指南",
            sub_title=f"探索{topic}的魅力与特色{location_context}"
        ))

        # 选项2: 地点相关标题
        if location_context:
            title_options.append(SevenStepTitleOption(
                main_title=f"{topic}{location_context}",
                sub_title=f"深入探访{topic}，发现独特体验{poi_context}"
            ))

        # 选项3: 问题式标题
        title_options.append(SevenStepTitleOption(
            main_title=f"如何更好地体验{topic}？",
            sub_title=f"实用指南与建议{location_context}"
        ))

        # 选项4: 列表式标题
        title_options.append(SevenStepTitleOption(
            main_title=f"{topic}的十大亮点",
            sub_title=f"不容错过的精彩内容{poi_context}"
        ))

        state["title_options"] = title_options
        state["current_step"] = 3
        state["status"] = "titles_generated"

        print(f"  生成{len(title_options)}个标题选项")

    except Exception as e:
        state["error"] = f"标题策划失败: {str(e)}"
        state["status"] = "error"

    return state


async def outline_generation_node(state: AdvancedAgentState) -> AdvancedAgentState:
    """大纲生成节点：生成文章大纲"""
    print("步骤4: 大纲生成")

    try:
        selected_title = state.get("selected_title")
        if not selected_title:
            # 如果没有选择标题，使用第一个选项
            title_options = state.get("title_options", [])
            if title_options:
                selected_title = title_options[0]
                state["selected_title"] = selected_title
            else:
                raise ValueError("没有可用的标题选项")

        main_title = selected_title.main_title
        rag_results = state.get("rag_results", [])
        nearby_pois = state.get("nearby_pois", [])

        # 生成大纲（实际应该调用AI模型）
        outline = []

        # 章节1: 引言
        outline.append(SevenStepOutlineSection(
            section=1,
            title="引言：开启探索之旅",
            points=[
                f"介绍{main_title}的背景和意义",
                "阐述本文的目的和结构",
                "引发读者的兴趣和期待"
            ]
        ))

        # 章节2: 核心内容
        outline.append(SevenStepOutlineSection(
            section=2,
            title=f"深入探索{main_title}",
            points=[
                "详细讲解核心概念和特点",
                "分析关键要素和影响因素",
                "提供实用建议和技巧"
            ]
        ))

        # 章节3: 地点信息（如果有）
        if nearby_pois:
            outline.append(SevenStepOutlineSection(
                section=3,
                title="周边地点推荐",
                points=[
                    f"介绍附近的{len(nearby_pois)}个重要地点",
                    "提供实用信息和参观建议",
                    "分享个人体验和感受"
                ]
            ))

        # 章节4: 实践指南
        outline.append(SevenStepOutlineSection(
            section=4,
            title="实用指南与建议",
            points=[
                "步骤-by-步骤的实施指南",
                "常见问题与解决方案",
                "注意事项和避坑指南"
            ]
        ))

        # 章节5: 总结
        outline.append(SevenStepOutlineSection(
            section=5,
            title="总结与展望",
            points=[
                "回顾全文核心内容",
                "强调重要观点和启示",
                "展望未来发展趋势"
            ]
        ))

        # 章节6: 附录（可选）
        if rag_results:
            outline.append(SevenStepOutlineSection(
                section=6,
                title="参考资料与延伸阅读",
                points=[
                    "相关文献和资源推荐",
                    "进一步学习建议",
                    "实用工具和网站推荐"
                ]
            ))

        state["outline"] = outline
        state["outline_quality_check"] = True
        state["current_step"] = 4
        state["status"] = "outline_generated"

        print(f"  生成{len(outline)}个章节的大纲")

    except Exception as e:
        state["error"] = f"大纲生成失败: {str(e)}"
        state["status"] = "error"

    return state


async def content_generation_node(state: AdvancedAgentState) -> AdvancedAgentState:
    """正文生成节点：根据大纲生成完整内容"""
    print("步骤5: 正文生成")

    try:
        outline = state.get("outline", [])
        selected_title = state.get("selected_title")
        rag_results = state.get("rag_results", [])
        nearby_pois = state.get("nearby_pois", [])

        if not outline:
            raise ValueError("没有可用的大纲")

        # 构建Markdown内容（实际应该调用AI模型）
        markdown_parts = []

        # 标题
        if selected_title:
            markdown_parts.append(f"# {selected_title.main_title}\n")
            if selected_title.sub_title:
                markdown_parts.append(f"*{selected_title.sub_title}*\n")

        # 生成时间
        markdown_parts.append(f"> 生成时间: {time.strftime('%Y年%m月%d日 %H:%M:%S')}\n")

        # 各章节内容
        for section in outline:
            markdown_parts.append(f"## {section.title}\n")

            # 章节要点
            for point in section.points:
                markdown_parts.append(f"- {point}")

            # 添加示例内容
            markdown_parts.append(f"\n这是关于'{section.title}'的详细内容...\n")

            # 如果是地点章节，添加POI信息
            if "地点" in section.title and nearby_pois:
                markdown_parts.append("### 周边地点推荐\n")
                for i, poi in enumerate(nearby_pois[:5], 1):
                    markdown_parts.append(f"{i}. **{poi.get('name', '')}**")
                    markdown_parts.append(f"   - 地址: {poi.get('address', '')}")
                    markdown_parts.append(f"   - 类型: {poi.get('type', '')}")
                    if poi.get('distance'):
                        markdown_parts.append(f"   - 距离: {poi.get('distance')}米")
                    markdown_parts.append("")

        # RAG检索内容引用
        if rag_results:
            markdown_parts.append("## 参考资料\n")
            for i, result in enumerate(rag_results[:3], 1):
                markdown_parts.append(f"{i}. {result.get('content', '')}")

        # 结束语
        markdown_parts.append("\n---\n")
        markdown_parts.append("*本文由ReWritter AI创作系统生成，仅供参考和学习使用。*")

        state["content_markdown"] = "\n".join(markdown_parts)
        state["content_quality_check"] = True
        state["current_step"] = 5
        state["status"] = "content_generated"

        print(f"  生成正文，字数: {len(state['content_markdown'])}")

    except Exception as e:
        state["error"] = f"正文生成失败: {str(e)}"
        state["status"] = "error"

    return state


async def image_planning_node(state: AdvancedAgentState) -> AdvancedAgentState:
    """配图规划节点：规划文章配图"""
    print("步骤6: 配图规划")

    try:
        outline = state.get("outline", [])
        nearby_pois = state.get("nearby_pois", [])

        image_plan = []

        # 封面图
        image_plan.append({
            "placeholder_id": "cover",
            "section_title": "封面",
            "description": "文章封面图片，体现主题和风格",
            "keywords": f"{state.get('topic', '')}, 封面, 主题图",
            "status": "planned"
        })

        # 各章节配图
        for i, section in enumerate(outline[:5], 1):  # 前5个章节
            image_plan.append({
                "placeholder_id": f"section_{i}",
                "section_title": section.title,
                "description": f" illustrating {section.title}",
                "keywords": f"{state.get('topic', '')}, {section.title}, 配图",
                "status": "planned"
            })

        # 地点配图（如果有POI）
        if nearby_pois:
            for i, poi in enumerate(nearby_pois[:3], 1):
                image_plan.append({
                    "placeholder_id": f"poi_{i}",
                    "section_title": poi.get("name", ""),
                    "description": f"{poi.get('name', '')}的实景图片",
                    "keywords": f"{poi.get('name', '')}, {poi.get('type', '')}, 实景",
                    "status": "planned"
                })

        state["image_plan"] = image_plan
        state["current_step"] = 6
        state["status"] = "image_planned"

        print(f"  规划{len(image_plan)}个配图")

    except Exception as e:
        state["error"] = f"配图规划失败: {str(e)}"
        state["status"] = "error"

    return state


async def final_synthesis_node(state: AdvancedAgentState) -> AdvancedAgentState:
    """图文合成节点：整合最终文档"""
    print("步骤7: 图文合成")

    try:
        content_markdown = state.get("content_markdown", "")
        image_plan = state.get("image_plan", [])

        if not content_markdown:
            raise ValueError("没有可用的正文内容")

        # 将图片占位符插入到Markdown中
        final_markdown = content_markdown

        # 在开头添加图片规划说明
        if image_plan:
            plan_text = "\n## 配图规划\n\n"
            for img in image_plan:
                plan_text += f"![{img['description']}]({img['placeholder_id']}.jpg)\n"
                plan_text += f"*{img['section_title']} - {img['description']}*\n\n"

            # 将图片规划插入到文档末尾之前
            if "## 参考资料" in final_markdown:
                # 插入到参考资料之前
                parts = final_markdown.split("## 参考资料")
                final_markdown = parts[0] + plan_text + "## 参考资料" + parts[1]
            else:
                # 添加到文档末尾
                final_markdown += "\n\n" + plan_text

        state["final_markdown"] = final_markdown
        state["current_step"] = 7
        state["status"] = "synthesis_completed"

        print(f"  合成最终文档，字数: {len(final_markdown)}")

    except Exception as e:
        state["error"] = f"图文合成失败: {str(e)}"
        state["status"] = "error"

    return state


async def publish_preparation_node(state: AdvancedAgentState) -> AdvancedAgentState:
    """发布准备节点：准备发布到平台"""
    print("步骤8: 发布准备")

    try:
        final_markdown = state.get("final_markdown", "")

        if not final_markdown:
            raise ValueError("没有可用的最终文档")

        # 这里可以添加发布到小红书等平台的准备逻辑
        # 例如：格式化内容、添加标签、设置发布时间等

        state["publish_ready"] = True
        state["publish_platform"] = "xiaohongshu"  # 默认发布到小红书
        state["current_step"] = 8
        state["status"] = "ready_for_publish"

        print("  发布准备完成")

    except Exception as e:
        state["error"] = f"发布准备失败: {str(e)}"
        state["status"] = "error"

    return state


# ==================== 工作流构建 ====================

def build_advanced_workflow() -> Any:
    """构建高级多Agent工作流"""
    print("构建高级多Agent工作流...")

    graph = StateGraph(AdvancedAgentState)

    # 添加节点
    graph.add_node("location_enhancement", location_enhancement_node)
    graph.add_node("rag_retrieval", rag_retrieval_node)
    graph.add_node("title_planning", title_planning_node)
    graph.add_node("outline_generation", outline_generation_node)
    graph.add_node("content_generation", content_generation_node)
    graph.add_node("image_planning", image_planning_node)
    graph.add_node("final_synthesis", final_synthesis_node)
    graph.add_node("publish_preparation", publish_preparation_node)

    # 定义工作流路径
    graph.add_edge(START, "location_enhancement")
    graph.add_edge("location_enhancement", "rag_retrieval")
    graph.add_edge("rag_retrieval", "title_planning")
    graph.add_edge("title_planning", "outline_generation")
    graph.add_edge("outline_generation", "content_generation")
    graph.add_edge("content_generation", "image_planning")
    graph.add_edge("image_planning", "final_synthesis")
    graph.add_edge("final_synthesis", "publish_preparation")
    graph.add_edge("publish_preparation", END)

    return graph.compile()


async def run_advanced_workflow(initial_state: AdvancedAgentState) -> AdvancedAgentState:
    """运行高级工作流"""
    print("开始运行高级工作流...")

    # 添加时间戳
    initial_state["start_time"] = time.time()
    initial_state["current_step"] = 0
    initial_state["status"] = "starting"

    # 构建并运行工作流
    app = build_advanced_workflow()

    try:
        result = await app.ainvoke(initial_state)
        result["end_time"] = time.time()
        result["status"] = "completed"

        duration = result["end_time"] - result["start_time"]
        print(f"工作流完成! 总耗时: {duration:.2f}秒")
        print(f"最终状态: {result['status']}")
        print(f"生成文档长度: {len(result.get('final_markdown', ''))}字符")

    except Exception as e:
        initial_state["error"] = str(e)
        initial_state["status"] = "failed"
        initial_state["end_time"] = time.time()
        print(f"工作流失败: {e}")
        result = initial_state

    return result


# ==================== 工具函数 ====================

def create_initial_state(
    topic: str,
    requirements: str = "",
    style: str = "",
    location: Optional[str] = None,
    user_id: str = "anonymous"
) -> AdvancedAgentState:
    """创建初始工作流状态"""
    return {
        "topic": topic,
        "requirements": requirements,
        "style": style,
        "location": location,
        "user_id": user_id,
        "current_step": 0,
        "status": "initialized",
        "start_time": time.time(),
    }


def get_workflow_progress(state: AdvancedAgentState) -> dict:
    """获取工作流进度信息"""
    total_steps = 8
    current_step = state.get("current_step", 0)
    status = state.get("status", "unknown")

    progress = {
        "current_step": current_step,
        "total_steps": total_steps,
        "progress_percentage": min(100, int((current_step / total_steps) * 100)),
        "status": status,
        "has_error": "error" in state,
        "error_message": state.get("error"),
        "start_time": state.get("start_time"),
        "end_time": state.get("end_time"),
    }

    if state.get("end_time") and state.get("start_time"):
        progress["duration_seconds"] = state["end_time"] - state["start_time"]

    return progress