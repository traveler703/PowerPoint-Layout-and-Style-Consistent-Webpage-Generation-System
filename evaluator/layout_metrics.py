"""布局质量：基于 HTML 字符串解析的绝对定位重叠启发式估计（无第三方 DOM 依赖）。"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class LayoutMetrics(BaseModel):
    overlap_ratio: float = Field(ge=0.0, le=1.0, description="0 = no overlap detected")
    overflow_count: int = Field(ge=0)
    absolute_boxes: int = Field(
        default=0,
        description="参与检测的 position:absolute/fixed 盒子数量",
    )


class _Rect:
    __slots__ = ("left", "top", "width", "height")

    def __init__(self, left: float, top: float, width: float, height: float) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    def area(self) -> float:
        return max(self.width, 0) * max(self.height, 0)


_STYLE_ATTR_RE = re.compile(
    r'(?is)\sstyle\s*=\s*(["\'])(.*?)\1',
)
_POSITION_BLOCK_RE = re.compile(r"position\s*:\s*(absolute|fixed)", re.I)


def _parse_px(val: str | None) -> float | None:
    if val is None:
        return None
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*px\s*$", val.strip())
    if m:
        return float(m.group(1))
    return None


def _parse_style_rect(style: str) -> _Rect | None:
    if not _POSITION_BLOCK_RE.search(style):
        return None
    pairs: dict[str, str] = {}
    for part in style.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            pairs[k.strip().lower()] = v.strip()
    left = _parse_px(pairs.get("left")) or 0.0
    top = _parse_px(pairs.get("top")) or 0.0
    w = _parse_px(pairs.get("width"))
    h = _parse_px(pairs.get("height"))
    if w is None or h is None:
        return None
    return _Rect(left=left, top=top, width=w, height=h)


def _intersection_area(a: _Rect, b: _Rect) -> float:
    x1 = max(a.left, b.left)
    y1 = max(a.top, b.top)
    x2 = min(a.left + a.width, b.left + b.width)
    y2 = min(a.top + a.height, b.top + b.height)
    iw = max(0.0, x2 - x1)
    ih = max(0.0, y2 - y1)
    return iw * ih


def overlap_ratio_from_html(html: str) -> LayoutMetrics:
    """扫描内联 ``style`` 中的 ``position:absolute|fixed`` + 像素宽高。"""
    rects: list[_Rect] = []
    for m in _STYLE_ATTR_RE.finditer(html):
        style = m.group(2)
        r = _parse_style_rect(style)
        if r and r.area() > 0:
            rects.append(r)
    if len(rects) < 2:
        return LayoutMetrics(
            overlap_ratio=0.0,
            overflow_count=0,
            absolute_boxes=len(rects),
        )
    total_overlap = 0.0
    total_area = sum(r.area() for r in rects)
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            total_overlap += _intersection_area(rects[i], rects[j])
    ratio = min(1.0, total_overlap / total_area) if total_area > 0 else 0.0
    return LayoutMetrics(overlap_ratio=ratio, overflow_count=0, absolute_boxes=len(rects))


def overlap_ratio_stub(html: str) -> LayoutMetrics:
    return overlap_ratio_from_html(html)
