"""Text readability heuristics for generated HTML fragments."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup


@dataclass
class ReadabilityMetrics:
    low_contrast_count: int = 0
    hidden_text_count: int = 0
    overflow_risk_count: int = 0
    issues: list[str] = field(default_factory=list)


_TEXT_TAGS = {"p", "span", "li", "td", "th", "label", "h1", "h2", "h3", "h4", "h5", "h6"}
_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}\b")
_RGB_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*(0|1|0?\.\d+))?\s*\)",
    re.I,
)


def _style_map(style: str | None) -> dict[str, str]:
    pairs: dict[str, str] = {}
    if not style:
        return pairs
    for part in style.split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            pairs[key.strip().lower()] = value.strip()
    return pairs


def _style_text(styles: dict[str, str]) -> str:
    return "; ".join(f"{key}: {value}" for key, value in styles.items() if value) + (
        ";" if styles else ""
    )


def _token_palette(tokens: dict[str, str] | None) -> dict[str, str]:
    if not tokens:
        return {}
    return {
        f"--{key}" if not key.startswith("--") else key: value
        for key, value in tokens.items()
        if isinstance(value, str)
    }


def _resolve_var(value: str, tokens: dict[str, str]) -> str:
    match = re.search(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]+))?\)", value)
    if not match:
        return value
    return tokens.get(match.group(1), (match.group(2) or value).strip())


def _parse_color(value: str | None, tokens: dict[str, str]) -> tuple[int, int, int, float] | None:
    if not value:
        return None
    value = _resolve_var(value.strip(), tokens)
    if value in {"transparent", "inherit", "currentColor", "initial", "unset"}:
        return None
    hex_match = _COLOR_RE.search(value)
    if hex_match:
        raw = hex_match.group(0).lstrip("#")
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), 1.0
    rgb_match = _RGB_RE.search(value)
    if rgb_match:
        alpha = float(rgb_match.group(4)) if rgb_match.group(4) is not None else 1.0
        return (
            min(255, int(rgb_match.group(1))),
            min(255, int(rgb_match.group(2))),
            min(255, int(rgb_match.group(3))),
            alpha,
        )
    return None


def _relative_luminance(rgb: tuple[int, int, int, float]) -> float:
    def channel(value: int) -> float:
        value = value / 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b, _ = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast_ratio(fg: tuple[int, int, int, float], bg: tuple[int, int, int, float]) -> float:
    light = max(_relative_luminance(fg), _relative_luminance(bg))
    dark = min(_relative_luminance(fg), _relative_luminance(bg))
    return (light + 0.05) / (dark + 0.05)


def _best_bw_for_background(bg: tuple[int, int, int, float]) -> str:
    white = (255, 255, 255, 1.0)
    black = (17, 24, 39, 1.0)
    return "#FFFFFF" if _contrast_ratio(white, bg) >= _contrast_ratio(black, bg) else "#111827"


def _parse_px(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"\s*(\d+(?:\.\d+)?)px\s*$", value)
    return float(match.group(1)) if match else None


def _nearest_style(node: Any, prop_names: tuple[str, ...]) -> str | None:
    cur = node
    while cur is not None and getattr(cur, "name", None):
        styles = _style_map(cur.get("style"))
        for prop in prop_names:
            if prop in styles:
                return styles[prop]
        cur = cur.parent
    return None


def _nearest_background(node: Any, tokens: dict[str, str]) -> tuple[int, int, int, float] | None:
    cur = node
    while cur is not None and getattr(cur, "name", None):
        styles = _style_map(cur.get("style"))
        bg = _parse_color(styles.get("background-color") or styles.get("background"), tokens)
        if bg and bg[3] > 0.35:
            return bg
        cur = cur.parent
    return None


def _has_direct_text(node: Any) -> bool:
    return any(getattr(child, "name", None) is None and str(child).strip() for child in node.children)


def readability_from_html(html: str, tokens: dict[str, str] | None = None) -> ReadabilityMetrics:
    """Detect low-contrast text, hidden text, and obvious fixed-box clipping risks."""
    soup = BeautifulSoup(html or "", "html.parser")
    palette = _token_palette(tokens)
    default_text = _parse_color(palette.get("--color-text") or "#111827", palette)
    default_bg = _parse_color(palette.get("--color-background") or "#FFFFFF", palette)
    metrics = ReadabilityMetrics()

    for node in soup.find_all(True):
        if node.name in {"script", "style", "svg"}:
            continue
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        styles = _style_map(node.get("style"))
        if (
            styles.get("display", "").lower() == "none"
            or styles.get("visibility", "").lower() == "hidden"
            or styles.get("opacity") in {"0", "0.0"}
        ):
            metrics.hidden_text_count += 1
            continue

        if node.name in _TEXT_TAGS or _has_direct_text(node):
            fg = _parse_color(_nearest_style(node, ("color",)), palette) or default_text
            bg = _parse_color(
                _nearest_style(node, ("background-color", "background")),
                palette,
            ) or default_bg
            if fg and fg[3] < 0.35:
                metrics.hidden_text_count += 1
            elif fg and bg and _contrast_ratio(fg, bg) < 3.2:
                metrics.low_contrast_count += 1

        width = _parse_px(styles.get("width"))
        height = _parse_px(styles.get("height") or styles.get("max-height"))
        overflow = styles.get("overflow", "")
        if width and height and "hidden" in overflow.lower():
            font_size = _parse_px(styles.get("font-size")) or 16
            line_height = _parse_px(styles.get("line-height")) or font_size * 1.35
            chars_per_line = max(4, int(width / max(font_size, 1) * 1.7))
            max_lines = max(1, int(height / max(line_height, 1)))
            if len(text) > chars_per_line * max_lines * 1.35:
                metrics.overflow_risk_count += 1

    if metrics.low_contrast_count:
        metrics.issues.append(f"{metrics.low_contrast_count}处文字与背景对比度过低")
    if metrics.hidden_text_count:
        metrics.issues.append(f"{metrics.hidden_text_count}处文字可能被隐藏或透明")
    if metrics.overflow_risk_count:
        metrics.issues.append(f"{metrics.overflow_risk_count}处固定高度文本容器存在截断风险")
    return metrics


def fix_readability_colors(html: str, tokens: dict[str, str] | None = None) -> tuple[str, int]:
    """
    Directly repair text color contrast without asking the LLM to regenerate.

    The fixer only changes inline styles on text-bearing nodes. It chooses
    black or white according to the nearest explicit background/card color.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    palette = _token_palette(tokens)
    default_bg = _parse_color(palette.get("--color-background") or "#FFFFFF", palette)
    default_text = _parse_color(palette.get("--color-text") or "#111827", palette)
    fixed = 0

    for node in soup.find_all(True):
        if node.name in {"script", "style", "svg"}:
            continue
        if not node.get_text(" ", strip=True):
            continue
        if node.name not in _TEXT_TAGS and not _has_direct_text(node):
            continue

        styles = _style_map(node.get("style"))
        fg = _parse_color(_nearest_style(node, ("color",)), palette) or default_text
        bg = _nearest_background(node, palette) or default_bg
        if not fg or not bg:
            continue

        should_fix = fg[3] < 0.6 or _contrast_ratio(fg, bg) < 4.5
        if not should_fix:
            continue

        styles["color"] = _best_bw_for_background(bg)
        if styles.get("opacity"):
            try:
                if float(styles["opacity"]) < 0.6:
                    styles["opacity"] = "1"
            except ValueError:
                pass
        if styles.get("visibility", "").lower() == "hidden":
            styles["visibility"] = "visible"
        node["style"] = _style_text(styles)
        fixed += 1

    return str(soup), fixed
