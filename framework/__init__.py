"""
Structured representation: style tokens, layout atoms, component specs.
Implementations live in tokens, layouts, and components.
"""

from framework.components import ComponentSpec, ComponentType
from framework.layouts import LayoutAtom, LayoutRegistry
from framework.tokens import StyleTokens, load_style_tokens

__all__ = [
    "ComponentSpec",
    "ComponentType",
    "LayoutAtom",
    "LayoutRegistry",
    "StyleTokens",
    "load_style_tokens",
]
