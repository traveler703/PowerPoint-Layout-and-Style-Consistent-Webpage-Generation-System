"""Stub PagePlan for backward compatibility."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PagePlan(BaseModel):
    """页面布局计划"""
    layout_id: str = "content"
    rationale: str = ""
    assignments: dict[str, Any] = {}


__all__ = ["PagePlan"]
