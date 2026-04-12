"""Design tokens (colors, typography, spacing) as data — inject into CSS or prompts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StyleTokens(BaseModel):
    """Maps semantic roles to concrete values (CSS variables or raw values)."""

    colors: dict[str, str] = Field(default_factory=dict)
    typography: dict[str, str] = Field(default_factory=dict)
    spacing: dict[str, str] = Field(default_factory=dict)
    radii: dict[str, str] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_css_variables_block(self) -> str:
        """Emit a :root { ... } snippet for demo / generated HTML."""
        lines: list[str] = [":root {"]
        for group_name, group in (
            ("color", self.colors),
            ("font", self.typography),
            ("space", self.spacing),
            ("radius", self.radii),
        ):
            for key, val in group.items():
                lines.append(f"  --{group_name}-{key}: {val};")
        for key, val in self.extra.items():
            if isinstance(val, str):
                lines.append(f"  --{key}: {val};")
        lines.append("}")
        return "\n".join(lines)


def load_style_tokens(path: str | Path) -> StyleTokens:
    """Load tokens from JSON. Team: replace or extend schema as design system grows."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return StyleTokens.model_validate(data)


def default_tokens() -> StyleTokens:
    """Minimal built-in defaults when no JSON file is present."""
    return StyleTokens(
        colors={"primary": "#1e40af", "surface": "#f8fafc", "text": "#0f172a"},
        typography={"heading": "system-ui, sans-serif", "body": "system-ui, sans-serif"},
        spacing={"sm": "0.5rem", "md": "1rem", "lg": "1.5rem"},
        radii={"card": "8px"},
    )
