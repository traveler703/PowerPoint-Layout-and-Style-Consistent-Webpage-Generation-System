"""RGB ↔ Lab 与 ΔE（CIE76）用于风格一致性评估。"""

from __future__ import annotations

import re
from typing import Iterable


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float] | None:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or not re.match(r"^[0-9a-fA-F]{6}$", h):
        return None
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _rgb_to_xyz(r: float, g: float, b: float) -> tuple[float, float, float]:
    def pivot(u: float) -> float:
        u = u / 255.0
        return ((u + 0.055) / 1.055) ** 2.4 if u > 0.04045 else u / 12.92

    r_, g_, b_ = pivot(r), pivot(g), pivot(b)
    x = r_ * 0.4124564 + g_ * 0.3575761 + b_ * 0.1804375
    y = r_ * 0.2126729 + g_ * 0.7151522 + b_ * 0.0721750
    z = r_ * 0.0193339 + g_ * 0.1191920 + b_ * 0.9503041
    return x, y, z


def _xyz_to_lab(x: float, y: float, z: float) -> tuple[float, float, float]:
    xn, yn, zn = 0.95047, 1.0, 1.08883
    def f(t: float) -> float:
        delta = 6 / 29
        return t ** (1 / 3) if t > delta**3 else t / (3 * delta**2) + 4 / 29

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b_ = 200 * (fy - fz)
    return L, a, b_


def hex_to_lab(hex_color: str) -> tuple[float, float, float] | None:
    rgb = _hex_to_rgb(hex_color)
    if rgb is None:
        return None
    x, y, z = _rgb_to_xyz(*rgb)
    return _xyz_to_lab(x, y, z)


def delta_e_cie76(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    return (
        (lab1[0] - lab2[0]) ** 2 + (lab1[1] - lab2[1]) ** 2 + (lab1[2] - lab2[2]) ** 2
    ) ** 0.5


def max_delta_e_vs_palette(sample_hexes: Iterable[str], palette_hexes: Iterable[str]) -> float:
    """样本色与调色板中最近色的最大 ΔE。"""
    palette_labs = [hex_to_lab(h) for h in palette_hexes]
    palette_labs = [p for p in palette_labs if p is not None]
    if not palette_labs:
        return 0.0
    worst = 0.0
    for h in sample_hexes:
        lab = hex_to_lab(h)
        if lab is None:
            continue
        best = min(delta_e_cie76(lab, pl) for pl in palette_labs)
        worst = max(worst, best)
    return worst
