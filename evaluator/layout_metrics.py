"""Layout quality: element overlap, overflow. Stub returns zeros; parse DOM or bbox later."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LayoutMetrics(BaseModel):
    overlap_ratio: float = Field(ge=0.0, le=1.0, description="0 = no overlap")
    overflow_count: int = Field(ge=0)


def overlap_ratio_stub(_html: str) -> LayoutMetrics:
    """TODO: parse layout boxes (e.g. Playwright + getBoundingClientRect)."""
    return LayoutMetrics(overlap_ratio=0.0, overflow_count=0)
