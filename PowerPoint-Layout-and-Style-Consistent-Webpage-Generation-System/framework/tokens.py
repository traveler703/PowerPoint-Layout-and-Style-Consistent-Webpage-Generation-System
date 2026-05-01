"""Stub StyleTokens for backward compatibility."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class StyleTokens(BaseModel):
    """样式令牌"""
    colors: dict[str, str] = {}
    
    def to_css_variables_block(self) -> str:
        """转换为 CSS 变量块"""
        lines = [":root {"]
        for key, value in self.colors.items():
            lines.append(f"  --{key}: {value};")
        lines.append("}")
        return "\n".join(lines)


__all__ = ["StyleTokens"]
