from __future__ import annotations

from dataclasses import dataclass

from app.schemas import SevenStepImagePlanItem, SevenStepOutlineSection


class ImagePlanProvider:
    """配图规划接口。当前仅输出占位计划，后续可替换真实实现。"""

    def plan(self, topic: str, outline: list[SevenStepOutlineSection], content: str) -> list[SevenStepImagePlanItem]:
        raise NotImplementedError


@dataclass
class PlaceholderImagePlanProvider(ImagePlanProvider):
    max_images: int = 4

    def plan(self, topic: str, outline: list[SevenStepOutlineSection], content: str) -> list[SevenStepImagePlanItem]:
        items: list[SevenStepImagePlanItem] = []
        for index, section in enumerate(outline[: self.max_images], start=1):
            keywords = f"{topic} {section.title}".strip()
            items.append(
                SevenStepImagePlanItem(
                    placeholder_id=f"IMG_{index}",
                    section_title=section.title,
                    description=f"{section.title} 场景配图",
                    keywords=keywords,
                    status="planned",
                )
            )
        return items
