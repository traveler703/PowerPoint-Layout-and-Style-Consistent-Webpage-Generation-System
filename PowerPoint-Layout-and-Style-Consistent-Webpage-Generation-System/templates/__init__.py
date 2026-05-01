"""Template-driven PPT generation system.

This module provides template-based HTML generation for consistent styling.
"""
from templates.template import Template, PageType, Placeholder
from templates.template_loader import TemplateLoader, load_template, list_available_templates
from templates.renderer import TemplateRenderer

__all__ = [
    "Template",
    "PageType",
    "Placeholder",
    "TemplateLoader",
    "load_template",
    "list_available_templates",
    "TemplateRenderer",
]
