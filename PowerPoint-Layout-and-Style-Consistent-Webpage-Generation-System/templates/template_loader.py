"""Template loader and registry."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

from templates.template import Template, PageTypeConfig, PageType

if TYPE_CHECKING:
    from templates.template import Template


class TemplateLoader:
    """Loads and manages PPT templates."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = templates_dir or self._default_templates_dir()
        self._registry: dict[str, Template] = {}
        self._load_all_templates()

    def _default_templates_dir(self) -> Path:
        """Get the default templates directory."""
        return Path(__file__).resolve().parent / "data"

    def _load_all_templates(self) -> None:
        """Load all templates from the templates directory."""
        if not self.templates_dir.exists():
            return

        loaded = set()
        for json_file in self.templates_dir.glob("*.json"):
            loaded.add(json_file.stem)
            try:
                template = self.load_from_file(json_file)
                self._registry[template.template_id] = template
            except Exception as e:
                print(f"Failed to load template {json_file}: {e}")

        # Also scan user_generated subdirectory
        user_dir = self.templates_dir / "user_generated"
        if user_dir.exists():
            for json_file in user_dir.glob("*.json"):
                if json_file.stem not in loaded:
                    try:
                        template = self.load_from_file(json_file)
                        self._registry[template.template_id] = template
                    except Exception as e:
                        print(f"Failed to load user template {json_file}: {e}")

    def load_from_file(self, path: Path | str) -> Template:
        """Load a template from a JSON file."""
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return self._parse_template_data(data)

    def _parse_template_data(self, data: dict) -> Template:
        """Parse template data into a Template object."""
        template_id = data.get("template_id", data.get("id", "unknown"))
        name = data.get("template_name", data.get("name", "Unnamed"))
        description = data.get("description", "")

        css_vars = data.get("css_variables", {})

        page_types = {}
        for type_key, type_config in data.get("page_types", {}).items():
            page_types[type_key] = PageTypeConfig(
                type_name=PageType(type_key),
                skeleton=type_config.get("skeleton", ""),
                placeholders=type_config.get("placeholders", []),
                content_patterns=type_config.get("content_patterns", {})
            )

        if "content" not in page_types:
            page_types["content"] = PageTypeConfig(
                type_name=PageType.CONTENT,
                skeleton=self._extract_default_skeleton(data.get("raw_html", "")),
                placeholders=["title", "content"],
                content_patterns={}
            )

        viewport_w, viewport_h = self._extract_viewport(data.get("raw_html", ""))

        return Template(
            template_id=template_id,
            name=name,
            description=description,
            css_variables=css_vars,
            page_types=page_types,
            raw_html=data.get("raw_html", ""),
            viewport_width=viewport_w,
            viewport_height=viewport_h,
            tags=data.get("tags", []),
            is_default=data.get("is_default", False)
        )

    def _extract_css_from_html(self, html: str) -> dict[str, str]:
        """Extract CSS variables from an HTML style block."""
        css_vars = {}

        # Extract style block
        style_match = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
        if not style_match:
            return css_vars

        style_content = style_match.group(1)

        # Look for common CSS variables
        color_patterns = [
            (r"--color-primary:\s*([^;]+);", "color-primary"),
            (r"--color-secondary:\s*([^;]+);", "color-secondary"),
            (r"--color-accent:\s*([^;]+);", "color-accent"),
            (r"--color-surface:\s*([^;]+);", "color-surface"),
            (r"--color-background:\s*([^;]+);", "color-background"),
            (r"background-color:\s*([^;]+);", "color-surface"),
        ]

        # Also look for raw colors used in the template
        color_values = re.findall(r"#(?:[0-9a-fA-F]{3}){1,2}", style_content)
        if color_values:
            unique_colors = list(dict.fromkeys(color_values))[:6]
            for i, color in enumerate(unique_colors):
                key = ["color-primary", "color-secondary", "color-accent", "color-surface", "color-background", "color-text"][i]
                css_vars[key] = color.strip()

        # Look for font-family
        font_match = re.search(r"font-family:\s*([^;]+);", style_content)
        if font_match:
            css_vars["font-body"] = font_match.group(1).strip().strip("'\"")

        return css_vars

    def _extract_viewport(self, html: str) -> tuple[int, int]:
        """Extract viewport dimensions from HTML."""
        # Look for .slide { width: ... height: ... }
        slide_match = re.search(r"\.slide\s*\{[^}]*width:\s*(\d+)px[^}]*height:\s*(\d+)px", html, re.DOTALL)
        if slide_match:
            return int(slide_match.group(1)), int(slide_match.group(2))

        # Fallback: look for any width/height
        width_match = re.search(r"width:\s*(\d+)px", html)
        height_match = re.search(r"height:\s*(\d+)px", html)

        return (
            int(width_match.group(1)) if width_match else 1280,
            int(height_match.group(1)) if height_match else 720
        )

    def _generate_skeleton_from_html(self, html: str) -> str:
        """Generate a skeleton by replacing content with placeholders."""
        skeleton = html

        # Remove script blocks
        skeleton = re.sub(r"<script[^>]*>.*?</script>", "", skeleton, flags=re.DOTALL)

        # Remove style blocks
        skeleton = re.sub(r"<style[^>]*>.*?</style>", "", skeleton, flags=re.DOTALL)

        # Replace common content patterns with placeholders
        skeleton = skeleton.replace("{{ page_title }}", "{{title}}")
        skeleton = skeleton.replace("{{ page_content }}", "{{content}}")
        skeleton = skeleton.replace("{{ current_page_number }}", "{{page_number}}")
        skeleton = skeleton.replace("{{ total_page_count }}", "{{total_pages}}")

        # Replace any remaining text content (simplified approach)
        # This is a basic implementation; can be enhanced

        return skeleton

    def _extract_cover_skeleton(self, html: str) -> str:
        """Extract cover page skeleton from HTML."""
        # Look for cover-related classes
        cover_match = re.search(r'<div[^>]*class="[^"]*cover[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        if cover_match:
            content = cover_match.group(1)
            content = re.sub(r"<[^>]+>", lambda m: m.group(0) if m.group(0).startswith("</") else m.group(0), content)
            return content

        # Fallback skeleton
        return """
        <div class="slide cover">
            <div class="title-box">
                <h1 class="main-title">{{title}}</h1>
                <p class="subtitle">{{subtitle}}</p>
                <div class="date-badge">{{date_badge}}</div>
            </div>
        </div>
        """

    def _extract_toc_skeleton(self, html: str) -> str:
        """Extract TOC page skeleton from HTML."""
        return """
        <div class="slide toc">
            <div class="page-title">{{title}}</div>
            <div class="page-content">
                <div class="toc-grid">
                    {{toc_items}}
                </div>
            </div>
        </div>
        """

    def _extract_compare_skeleton(self, html: str) -> str:
        """Extract comparison page skeleton from HTML."""
        return """
        <div class="slide compare">
            <div class="page-title">{{title}}</div>
            <div class="page-content">
                <div class="compare-grid">
                    {{items}}
                </div>
            </div>
        </div>
        """

    def _extract_timeline_skeleton(self, html: str) -> str:
        """Extract timeline page skeleton from HTML."""
        return """
        <div class="slide timeline">
            <div class="page-title">{{title}}</div>
            <div class="page-content">
                <div class="timeline-container">
                    {{timeline_items}}
                </div>
            </div>
        </div>
        """

    def _extract_default_skeleton(self, html: str) -> str:
        """Extract a default skeleton for content pages."""
        return """
        <div class="slide content">
            <div class="page-title">{{title}}</div>
            <div class="page-content">
                {{content}}
            </div>
            <div class="pagination">
                <span class="current-page">{{page_number}}</span> / <span class="total-pages">{{total_pages}}</span>
            </div>
        </div>
        """

    def get(self, template_id: str) -> Template | None:
        """Get a template by ID."""
        return self._registry.get(template_id)

    def get_or_default(self, template_id: str) -> Template:
        """Get a template by ID, or return the first available template."""
        template = self._registry.get(template_id)
        if template:
            return template

        if self._registry:
            return next(iter(self._registry.values()))

        raise ValueError(f"No templates available and requested '{template_id}'")

    def list_templates(self) -> list[Template]:
        """List all available templates."""
        return list(self._registry.values())

    def register(self, template: Template) -> None:
        """Register a new template."""
        self._registry[template.template_id] = template


# Global loader instance
_loader: TemplateLoader | None = None


def get_loader() -> TemplateLoader:
    """Get the global template loader instance."""
    global _loader
    if _loader is None:
        _loader = TemplateLoader()
    return _loader


def load_template(template_id: str) -> Template:
    """Convenience function to load a template by ID."""
    return get_loader().get_or_default(template_id)


def list_available_templates() -> list[Template]:
    """Convenience function to list all available templates."""
    return get_loader().list_templates()
