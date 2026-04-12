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


class ReasoningEngineBase(ABC):
    """Optional OO base class if you prefer subclassing over Protocol."""

    @abstractmethod
    def plan_page(self, semantic: SemanticPageInput, registry: LayoutRegistry) -> PagePlan:
        raise NotImplementedError
