"""视觉一致性：从 HTML 文本提取颜色并与风格令牌比对（ΔE）。"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from pydantic import BaseModel, Field

from evaluator.color_utils import delta_e_cie76, hex_to_lab, max_delta_e_vs_palette
from framework.tokens import StyleTokens


class StyleMetrics(BaseModel):
    max_color_delta_e: float | None = Field(
        default=None,
        description="相对调色板的最大 ΔE；越小越一致",
    )
    global_color_deviation_percent: float | None = Field(
        default=None,
        description="将 max ΔE 映射到 0–100 的粗略百分比，便于展示",
    )
    token_violations: list[str] = Field(default_factory=list)


_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}\b")
_STYLE_RE = re.compile(r"(?is)<style[^>]*>([\s\S]*?)</style>")
_RUNTIME_STYLE_RE = re.compile(
    r'(?is)<style[^>]*\bid\s*=\s*(["\'])landppt-runtime-overrides\1[^>]*>.*?</style>'
)
_RGB_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)",
    re.I,
)


def _normalize_hex(color: str) -> str:
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return f"#{value.upper()}"


def _extract_colors_from_css_text(css: str) -> list[str]:
    colors = [_normalize_hex(m.group(0)) for m in _HEX_RE.finditer(css)]
    for match in _RGB_RE.finditer(css):
        rgb = tuple(min(255, int(match.group(i))) for i in range(1, 4))
        colors.append("#{:02X}{:02X}{:02X}".format(*rgb))
    return colors


def extract_color_counts_from_html(html: str) -> Counter[str]:
    """Extract authored colors, excluding renderer-only runtime helper styles."""
    found: Counter[str] = Counter()
    authored_html = _RUNTIME_STYLE_RE.sub("", html)
    for m in _STYLE_RE.finditer(authored_html):
        found.update(_extract_colors_from_css_text(m.group(1)))
    for m in re.finditer(
        r'(?is)\sstyle\s*=\s*(["\'])(.*?)\1',
        authored_html,
    ):
        found.update(_extract_colors_from_css_text(m.group(2)))
    return found


def extract_colors_from_html(html: str) -> set[str]:
    return set(extract_color_counts_from_html(html))


def _palette_from_tokens(tokens: StyleTokens) -> list[str]:
    vals: list[str] = []
    for c in tokens.colors.values():
        if isinstance(c, str) and c.startswith("#"):
            vals.append(c)
    for k, v in tokens.extra.items():
        if isinstance(v, str) and v.startswith("#") and "color" in k.lower():
            vals.append(v)
    return vals


def _nearest_delta_e(hex_color: str, palette_labs: list[tuple[float, float, float]]) -> float | None:
    lab = hex_to_lab(hex_color)
    if lab is None or not palette_labs:
        return None
    return min(delta_e_cie76(lab, pl) for pl in palette_labs)


def _palette_deviation_percent(
    sample: Counter[str],
    palette: list[str],
    tolerance: float = 25.0,
) -> float:
    """Return the usage-weighted share of authored colors outside the palette."""
    palette_labs = [hex_to_lab(h) for h in palette]
    palette_labs = [p for p in palette_labs if p is not None]
    if not sample or not palette_labs:
        return 0.0
    checked = 0
    off_palette = 0
    for color, occurrences in sample.items():
        delta = _nearest_delta_e(color, palette_labs)
        if delta is None:
            continue
        checked += occurrences
        if delta > tolerance:
            off_palette += occurrences
    return (off_palette / checked) * 100 if checked else 0.0


def color_consistency_from_html(
    html: str,
    tokens: StyleTokens | dict[str, str] | None = None,
) -> StyleMetrics:
    """
    Check color consistency between HTML output and style tokens.

    Args:
        html: The generated HTML
        tokens: Style tokens (StyleTokens, dict of CSS variables, or None)

    Returns:
        StyleMetrics with consistency evaluation
    """
    # Extract palette from tokens
    palette: list[str] = []

    if tokens is None:
        return StyleMetrics(
            max_color_delta_e=None,
            global_color_deviation_percent=None,
            token_violations=["未定义调色板颜色"],
        )

    # Support both StyleTokens and plain dict
    if isinstance(tokens, dict):
        # Extract hex colors from dict values
        for v in tokens.values():
            if isinstance(v, str) and v.startswith("#"):
                palette.append(v)
    elif isinstance(tokens, StyleTokens):
        palette = _palette_from_tokens(tokens)

    # Accessibility text colors are allowed even when they are not part of a
    # decorative template palette. Readability fixes use these values directly.
    palette.extend(["#FFFFFF", "#111827", "#000000"])

    sample_counts = extract_color_counts_from_html(html)
    sample = set(sample_counts)
    if not palette:
        return StyleMetrics(
            max_color_delta_e=None,
            global_color_deviation_percent=None,
            token_violations=["未定义调色板颜色"],
        )
    if not sample:
        return StyleMetrics(
            max_color_delta_e=0.0,
            global_color_deviation_percent=0.0,
            token_violations=[],
        )
    worst = max_delta_e_vs_palette(sample, palette)
    pct = _palette_deviation_percent(sample_counts, palette)
    violations: list[str] = []
    if pct > 5.0:
        violations.append(f"全局颜色偏差约 {pct:.1f}%（目标 ≤5%）")
    return StyleMetrics(
        max_color_delta_e=worst,
        global_color_deviation_percent=pct,
        token_violations=violations,
    )


def color_delta_stub(html: str, tokens: StyleTokens) -> StyleMetrics:
    return color_consistency_from_html(html, tokens)


def aggregate_color_deviation(per_page: Iterable[StyleMetrics]) -> float:
    vals = [m.global_color_deviation_percent for m in per_page if m.global_color_deviation_percent is not None]
    return sum(vals) / len(vals) if vals else 0.0
