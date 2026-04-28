"""Component specifications: normalized content elements for layout + generation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    TEXT = "text"
    BULLETS = "bullets"
    IMAGE = "image"
    CHART = "chart"
    TABLE = "table"
    CUSTOM = "custom"


class ComponentSpec(BaseModel):
    """One logical component instance on a slide/page."""

    id: str
    type: ComponentType
    payload: dict[str, Any] = Field(default_factory=dict)
    style_hints: dict[str, str] = Field(default_factory=dict)
