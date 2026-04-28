"""Choose layout + assign components to slots. Replace StubReasoningEngine with LLM/heuristics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from pydantic import BaseModel, Field

from engine.types import SemanticPageInput
from framework.components import ComponentSpec
from framework.layouts import LayoutAtom, LayoutRegistry


class PagePlan(BaseModel):
    """Output of the reasoning engine for one page."""

    layout_id: str
    assignments: dict[str, str] = Field(
        default_factory=dict,
        description="slot_id -> component_id",
    )
    components: list[ComponentSpec] = Field(default_factory=list)
    rationale: str | None = None


class ReasoningEngine(Protocol):
    def plan_page(self, semantic: SemanticPageInput, registry: LayoutRegistry) -> PagePlan: ...


class StubReasoningEngine:
    """Deterministic placeholder: first registered layout + empty assignments."""

    def plan_page(self, semantic: SemanticPageInput, registry: LayoutRegistry) -> PagePlan:
        atoms = registry.all()
        layout: LayoutAtom | None = atoms[0] if atoms else None
        layout_id = layout.id if layout else "unknown"
        return PagePlan(
            layout_id=layout_id,
            assignments={},
            components=[],
            rationale="stub: pick first layout; implement LLM or CSP here.",
        )


class HeuristicReasoningEngine:
    """根据要点数量、图片、表格、图表与文本长度选择版式。"""

    def plan_page(self, semantic: SemanticPageInput, registry: LayoutRegistry) -> PagePlan:
        atoms = {a.id: a for a in registry.all()}
        n = semantic.effective_bullet_count()
        text_len = semantic.text_length()
        long_text = text_len > 400

        chosen_id: str | None = None
        rationale_parts: list[str] = []

        if semantic.has_table and semantic.table and "table-focus" in atoms:
            chosen_id = "table-focus"
            rationale_parts.append("检测到表格，选用表格版式")
        elif semantic.has_chart and "chart-focus" in atoms:
            chosen_id = "chart-focus"
            rationale_parts.append("标记为图表页，选用图表版式")
        elif semantic.image_urls:
            if long_text and "image-text-top" in atoms:
                chosen_id = "image-text-top"
                rationale_parts.append("含图片且正文较长，选用上图下文")
            elif "image-text-left" in atoms:
                chosen_id = "image-text-left"
                rationale_parts.append("含图片，选用左图右文")

        if chosen_id is None:
            if n >= 3 and "three-column" in atoms:
                chosen_id = "three-column"
                rationale_parts.append(f"要点数 {n}≥3，选用三栏")
            elif n == 2 and "two-column" in atoms:
                chosen_id = "two-column"
                rationale_parts.append("要点数为 2，选用双栏")
            elif "hero-title-body" in atoms:
                chosen_id = "hero-title-body"
                rationale_parts.append("默认单栏标题+正文")

        if chosen_id is None or chosen_id not in atoms:
            fallback = next(iter(atoms.keys()), "hero-title-body")
            chosen_id = fallback
            rationale_parts.append("回退到可用版式")

        layout = atoms[chosen_id]
        assignments = {s.id: s.role for s in layout.slots}
        return PagePlan(
            layout_id=chosen_id,
            assignments=assignments,
            components=[],
            rationale="；".join(rationale_parts),
        )


class ReasoningEngineBase(ABC):
    """Optional OO base class if you prefer subclassing over Protocol."""

    @abstractmethod
    def plan_page(self, semantic: SemanticPageInput, registry: LayoutRegistry) -> PagePlan:
        raise NotImplementedError
