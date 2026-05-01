"""Template data structures for PPT generation."""

from __future__ import annotations

import re
from typing import Any
from enum import Enum

from pydantic import BaseModel, Field


class PageType(str, Enum):
    """Supported page/slide types in a template."""

    COVER = "cover"      # Title/cover page
    CONTENT = "content"  # Regular content page
    TOC = "toc"          # Table of contents
    COMPARE = "compare"  # Comparison page
    CHART = "chart"     # Chart/data visualization
    TIMELINE = "timeline" # Timeline page
    QA = "qa"           # Q&A page
    ENDING = "ending"   # Ending/thank you page
    UNKNOWN = "unknown"  # Auto-detected or fallback


class Placeholder(BaseModel):
    """A placeholder in a template that needs to be filled."""

    key: str = Field(description="Placeholder identifier, e.g. 'title', 'content'")
    html_pattern: str = Field(description="HTML pattern for this placeholder")
    default_value: str = Field(default="", description="Default value if not provided")
    content_type: str = Field(
        default="text",
        description="Content type: text, html, list, image, chart"
    )


class PageTypeConfig(BaseModel):
    """Configuration for a specific page type within a template."""

    type_name: PageType = Field(description="The page type identifier")
    skeleton: str = Field(description="HTML skeleton with {{placeholder}} tags")
    placeholders: list[str] = Field(
        default_factory=list,
        description="List of placeholder keys used in this skeleton"
    )
    content_patterns: dict[str, str] = Field(
        default_factory=dict,
        description="Regex patterns for extracting content from user input"
    )


class Template(BaseModel):
    """A complete PPT template with styling and layout definitions."""

    template_id: str = Field(description="Unique template identifier")
    name: str = Field(description="Human-readable template name")
    description: str = Field(default="", description="Template description")

    # CSS variables for consistent styling
    css_variables: dict[str, str] = Field(
        default_factory=dict,
        description="CSS custom properties (color-*, font-*, space-*)"
    )

    # Page type configurations
    page_types: dict[str, PageTypeConfig] = Field(
        default_factory=dict,
        description="Configurations for each page type"
    )

    # Complete HTML template
    raw_html: str = Field(description="Complete HTML template with all CSS and JS")

    # Computed from raw_html
    viewport_width: int = Field(default=1280, description="Slide width in pixels")
    viewport_height: int = Field(default=720, description="Slide height in pixels")

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Template tags/categories")
    is_default: bool = Field(default=False, description="Is this the default template")
    version: str = Field(default="1.0.0", description="Template version")

    class Config:
        use_enum_values = True

    def get_page_type_config(self, page_type: str) -> PageTypeConfig | None:
        """Get configuration for a specific page type."""
        return self.page_types.get(page_type)

    def to_css_variables_block(self) -> str:
        """Convert CSS variables to a :root block."""
        if not self.css_variables:
            return ""
        lines = [":root {"]
        for key, value in self.css_variables.items():
            lines.append(f"  --{key}: {value};")
        lines.append("}")
        return "\n".join(lines)

    def infer_page_type(self, semantic_input: Any) -> str:
        """
        Infer the appropriate page type based on content.
        Override this method for custom inference logic.
        """
        # Simple heuristic based on content structure
        if hasattr(semantic_input, 'bullet_points'):
            bullet_count = len(semantic_input.bullet_points or [])
            if bullet_count >= 4:
                return PageType.TOC
            elif bullet_count == 0 and semantic_input.title:
                return PageType.COVER

        return PageType.CONTENT

    def extract_placeholders(self, html: str) -> list[Placeholder]:
        """Extract all {{placeholder}} patterns from HTML."""
        pattern = r"\{\{(\w+)\}\}"
        matches = re.findall(pattern, html)
        seen = set()
        placeholders = []
        for key in matches:
            if key not in seen:
                seen.add(key)
                placeholders.append(Placeholder(
                    key=key,
                    html_pattern=f"{{{{{key}}}}}",
                    content_type="text"
                ))
        return placeholders
