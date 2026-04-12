"""Shared types between engine and generator."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SemanticPageInput(BaseModel):
    """Per-page semantic hints produced by upstream content extraction (stub)."""

    page_index: int = 0
    title: str | None = None
    summary: str | None = None
    bullet_points: list[str] = Field(default_factory=list)
    has_chart: bool = False
    has_table: bool = False
    raw_notes: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
