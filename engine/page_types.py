"""Canonical page type names and compatibility helpers."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any


class PageType(str, Enum):
    """Page types shared by parsing, generation, templates, and API payloads."""

    COVER = "cover"
    CONTENT = "content"
    TOC = "toc"
    SECTION = "section"
    ENDING = "ending"
    COMPARE = "compare"
    CHART = "chart"
    TIMELINE = "timeline"
    QA = "qa"
    HERO_TITLE_BODY = "hero-title-body"
    TWO_COLUMN = "two-column"
    THREE_COLUMN = "three-column"
    IMAGE_TEXT_LEFT = "image-text-left"
    IMAGE_TEXT_TOP = "image-text-top"
    CHART_FOCUS = "chart-focus"
    TABLE_FOCUS = "table-focus"
    TITLE_ONLY = "title-only"
    QUOTE_HIGHLIGHT = "quote-highlight"
    COMPARISON = "comparison"
    STATISTICS = "statistics"
    UNKNOWN = "unknown"


PAGE_TYPE_ALIASES: dict[str, PageType] = {
    "title": PageType.COVER,
    "end": PageType.ENDING,
}


def normalize_page_type(
    value: Any,
    *,
    default: PageType = PageType.CONTENT,
) -> str:
    """Return a canonical page type while accepting historical aliases."""

    if isinstance(value, PageType):
        return value.value

    normalized = str(value or "").strip().lower()
    if not normalized:
        return default.value
    if normalized in PAGE_TYPE_ALIASES:
        return PAGE_TYPE_ALIASES[normalized].value

    try:
        return PageType(normalized).value
    except ValueError:
        return normalized


def page_type_from_mapping(
    page: Mapping[str, Any],
    *,
    default: PageType = PageType.CONTENT,
) -> str:
    """Read and normalize page type fields used by current and legacy clients."""

    raw_value = (
        page.get("page_type")
        or page.get("slide_type")
        or page.get("type")
        or page.get("layout")
    )
    return normalize_page_type(raw_value, default=default)


def normalize_page_payload(page: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a page payload and expose its canonical type as ``page_type``."""

    normalized = dict(page)
    normalized["page_type"] = page_type_from_mapping(page)
    return normalized
