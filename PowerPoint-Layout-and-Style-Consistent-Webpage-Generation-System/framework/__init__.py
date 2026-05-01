"""Stub StyleTokens for backward compatibility."""

from __future__ import annotations

from typing import Any


class StyleTokens:
    """样式令牌"""
    
    def __init__(self, colors: dict[str, str] | None = None):
        self.colors = colors or {}
    
    def to_css_variables_block(self) -> str:
        """转换为 CSS 变量块"""
        lines = [":root {"]
        for key, value in self.colors.items():
            lines.append(f"  --{key}: {value};")
        lines.append("}")
        return "\n".join(lines)
    
    def model_dump_json(self, **kwargs) -> str:
        """导出为 JSON"""
        import json
        return json.dumps({"colors": self.colors}, **kwargs)


__all__ = ["StyleTokens"]
