"""Visual consistency vs StyleTokens (e.g. ΔE color distance)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from framework.tokens import StyleTokens


class StyleMetrics(BaseModel):
    max_color_delta_e: float | None = Field(
        default=None,
        description="Max ΔE vs reference palette; None if not computed",
    )
    token_violations: list[str] = Field(default_factory=list)


def color_delta_stub(_html: str, _tokens: StyleTokens) -> StyleMetrics:
    """TODO: extract used colors from CSS/computed styles and compare to tokens."""
    return StyleMetrics(max_color_delta_e=None, token_violations=[])
