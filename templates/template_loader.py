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
            skeleton = self._sanitize_page_skeleton(
                type_key,
                type_config.get("skeleton", ""),
            )
            page_types[type_key] = PageTypeConfig(
                type_name=PageType(type_key),
                skeleton=skeleton,
                placeholders=self._infer_placeholders(type_key, type_config.get("placeholders", [])),
                content_patterns=type_config.get("content_patterns", {})
            )

        if "content" not in page_types:
            page_types["content"] = PageTypeConfig(
                type_name=PageType.CONTENT,
                skeleton=self._extract_default_skeleton(data.get("raw_html", "")),
                placeholders=["title", "content", "page_number"],
                content_patterns={}
            )

        # Auto-generate default skeletons for missing page types
        css_vars = data.get("css_variables", {})
        bg = css_vars.get("color-background", "#0a0a0a")
        text = css_vars.get("color-text", "#e0e0e0")
        accent = css_vars.get("color-accent", css_vars.get("color-primary", "#6366f1"))
        muted = css_vars.get("color-text-muted", "#888")
        heading = css_vars.get("font-heading", css_vars.get("font-body", "sans-serif"))

        if "cover" not in page_types:
            page_types["cover"] = PageTypeConfig(
                type_name=PageType.COVER,
                skeleton=(
                    f'<div class="slide cover" style="background:{bg};position:relative;'
                    'overflow:hidden;width:1280px;height:720px;">'
                    f'<h1 class="main-title" style="position:absolute;top:45%;left:50%;'
                    'transform:translate(-50%,-50%);font-size:56px;'
                    f'font-family:{heading};color:{text};text-align:center;">'
                    '{{title}}</h1>'
                    f'<p class="subtitle" style="position:absolute;top:calc(45% + 70px);'
                    'left:50%;transform:translateX(-50%);font-size:24px;color:{muted};">'
                    '{{subtitle}}</p>'
                    f'<div class="date-badge" style="position:absolute;bottom:120px;'
                    'left:50%;transform:translateX(-50%);font-size:16px;color:{accent};">'
                    '{{date_badge}}</div>'
                    '<div class="slide-footer" style="position:absolute;bottom:15px;'
                    'left:0;right:0;text-align:center;">'
                    '<span class="page-num">{{page_number}}</span></div>'
                    '</div>'
                ),
                placeholders=["title", "subtitle", "date_badge", "page_number"],
            )
        if "toc" not in page_types:
            page_types["toc"] = PageTypeConfig(
                type_name=PageType.TOC,
                skeleton=(
                    f'<div class="slide toc" style="background:{bg};position:relative;'
                    'overflow:hidden;width:1280px;height:720px;">'
                    f'<div class="page-title" style="position:absolute;top:40px;left:60px;'
                    f'font-size:32px;color:{accent};font-weight:700;">{{title}}</div>'
                    f'<div class="page-content" style="position:absolute;top:130px;'
                    'left:60px;right:60px;bottom:60px;">{{toc_items}}</div>'
                    '<div class="slide-footer" style="position:absolute;bottom:15px;'
                    'left:0;right:0;text-align:center;">'
                    '<span class="page-num">{{page_number}}</span></div>'
                    '</div>'
                ),
                placeholders=["title", "toc_items", "page_number"],
            )
        if "section" not in page_types:
            page_types["section"] = PageTypeConfig(
                type_name=PageType.SECTION,
                skeleton=(
                    f'<div class="slide section" style="background:{bg};position:relative;'
                    'overflow:hidden;width:1280px;height:720px;">'
                    f'<div class="page-title" style="position:absolute;top:60px;left:80px;'
                    f'font-size:18px;color:{accent};letter-spacing:6px;">{{chapter_tag}}</div>'
                    f'<h1 class="section-title" style="position:absolute;top:50%;left:50%;'
                    'transform:translate(-50%,-50%);font-size:48px;'
                    f'font-family:{heading};color:{text};text-align:center;">{{title}}</h1>'
                    f'<p class="subtitle" style="position:absolute;top:calc(50% + 70px);'
                    'left:50%;transform:translateX(-50%);font-size:20px;color:{muted};">'
                    '{{subtitle}}</p>'
                    '<div class="slide-footer" style="position:absolute;bottom:15px;'
                    'left:0;right:0;text-align:center;">'
                    '<span class="page-num">{{page_number}}</span></div>'
                    '</div>'
                ),
                placeholders=["chapter_tag", "title", "subtitle", "page_number"],
            )
        if "ending" not in page_types:
            page_types["ending"] = PageTypeConfig(
                type_name=PageType.ENDING,
                skeleton=(
                    f'<div class="slide ending" style="background:{bg};position:relative;'
                    'overflow:hidden;width:1280px;height:720px;">'
                    f'<div class="ending-content" style="position:absolute;top:50%;left:50%;'
                    'transform:translate(-50%,-50%);text-align:center;">'
                    f'<h1 style="font-size:48px;font-family:{heading};color:{text};">{{title}}</h1>'
                    f'<p class="ending-message" style="font-size:20px;color:{muted};'
                    'margin-top:16px;">{{message}}</p>'
                    '</div>'
                    '<div class="slide-footer" style="position:absolute;bottom:15px;'
                    'left:0;right:0;text-align:center;">'
                    '<span class="page-num">{{page_number}}</span></div>'
                    '</div>'
                ),
                placeholders=["title", "message", "page_number"],
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

    def _infer_placeholders(self, page_type: str, existing: list[str]) -> list[str]:
        """Return the standard placeholders for a page type, preserving extras."""
        required = {
            "cover": ["title", "subtitle", "date_badge", "page_number"],
            "toc": ["title", "toc_items", "page_number"],
            "section": ["chapter_tag", "title", "subtitle", "page_number"],
            "content": ["title", "content", "page_number"],
            "ending": ["title", "message", "page_number"],
        }.get(page_type, ["title", "page_number"])
        result = []
        for key in [*required, *(existing or [])]:
            if key not in result:
                result.append(key)
        return result

    def _sanitize_page_skeleton(self, page_type: str, skeleton: str) -> str:
        """Repair common LLM/user-template skeleton mistakes at load time."""
        if not skeleton:
            return skeleton

        skeleton = self._normalize_placeholder_spelling(skeleton)

        try:
            from bs4 import BeautifulSoup
        except Exception:
            return self._sanitize_page_skeleton_regex(page_type, skeleton)

        soup = BeautifulSoup(skeleton, "html.parser")
        root = soup.find("div", class_=lambda c: c and "slide" in str(c).split())
        if root is None:
            return self._sanitize_page_skeleton_regex(page_type, skeleton)

        if page_type == "cover":
            title_node = root.select_one("h1, .main-title, .title, .cover-title")
            if title_node:
                title_node.clear()
                title_node.append("{{title}}")
            subtitle_node = root.select_one(".subtitle, .sub-title, .cover-subtitle")
            if subtitle_node:
                subtitle_node.clear()
                subtitle_node.append("{{subtitle}}")
            date_node = root.select_one(".date-badge, .date")
            if date_node:
                date_node.clear()
                date_node.append("{{date_badge}}")

        elif page_type == "toc":
            self._remove_sample_siblings(root, ("toc-layout", "toc-list", "toc-grid"))
            title_node = root.select_one(".page-title, h1, h2")
            if title_node:
                title_node.clear()
                title_node.append("{{title}}")
            content_node = self._ensure_page_content(soup, root)
            content_node.clear()
            content_node.append("{{toc_items}}")

        elif page_type == "section":
            chapter_node = root.select_one(".page-title")
            if chapter_node:
                chapter_node.clear()
                chapter_node.append("{{chapter_tag}}")
            else:
                chapter_node = soup.new_tag("div")
                chapter_node["class"] = "page-title"
                chapter_node.append("{{chapter_tag}}")
                root.insert(0, chapter_node)
            title_node = root.select_one(".section-title, h1")
            if title_node:
                title_node.clear()
                title_node.append("{{title}}")
            else:
                title_node = soup.new_tag("h1")
                title_node["class"] = "section-title"
                title_node.append("{{title}}")
                root.append(title_node)
            subtitle_node = root.select_one(".subtitle")
            if subtitle_node:
                subtitle_node.clear()
                subtitle_node.append("{{subtitle}}")
            else:
                subtitle_node = soup.new_tag("p")
                subtitle_node["class"] = "subtitle"
                subtitle_node.append("{{subtitle}}")

            content_wrap = root.select_one(".section-content")
            if content_wrap is None:
                content_wrap = soup.new_tag("div")
                content_wrap["class"] = "section-content"
                insert_at = 0
                for idx, child in enumerate(list(root.children)):
                    if getattr(child, "name", None) and "slide-footer" not in str(child.get("class", [])).split():
                        insert_at = idx
                        break
                root.insert(insert_at, content_wrap)
            for node in (chapter_node, title_node, subtitle_node):
                if node and node.parent is not content_wrap:
                    content_wrap.append(node.extract())

        elif page_type == "content":
            self._remove_sample_siblings(
                root,
                (
                    "content-display",
                    "content-text",
                    "content-visual",
                    "actual-content",
                    "sample-content",
                    "placeholder-text",
                ),
            )
            title_node = root.select_one(".page-title, h1, h2")
            if title_node:
                title_node.clear()
                title_node.append("{{title}}")
            else:
                title_node = soup.new_tag("div")
                title_node["class"] = "page-title"
                title_node.append("{{title}}")
                root.insert(0, title_node)
            content_node = self._ensure_page_content(soup, root)
            content_node.clear()
            content_node.append("{{content}}")

        elif page_type == "ending":
            title_node = root.select_one(".ending-content h1, h1")
            if title_node:
                title_node.clear()
                title_node.append("{{title}}")
            message_node = root.select_one(".ending-message, .ending-content p")
            if message_node:
                message_node.clear()
                message_node.append("{{message}}")

        self._ensure_footer(soup, root)
        return str(root)

    def _sanitize_page_skeleton_regex(self, page_type: str, skeleton: str) -> str:
        """Regex fallback for environments without BeautifulSoup."""
        if page_type == "content":
            skeleton = re.sub(
                r'(<div[^>]*class="[^"]*\bpage-content\b[^"]*"[^>]*>).*?(</div>)',
                r"\1{{content}}\2",
                skeleton,
                flags=re.DOTALL | re.IGNORECASE,
            )
            skeleton = re.sub(
                r'<div[^>]*class="[^"]*\b(?:content-display|actual-content|sample-content|placeholder-text)\b[^"]*"[^>]*>.*?</div>',
                "",
                skeleton,
                flags=re.DOTALL | re.IGNORECASE,
            )
        elif page_type == "toc":
            skeleton = re.sub(
                r'(<div[^>]*class="[^"]*\bpage-content\b[^"]*"[^>]*>).*?(</div>)',
                r"\1{{toc_items}}\2",
                skeleton,
                flags=re.DOTALL | re.IGNORECASE,
            )
        return skeleton

    def _normalize_placeholder_spelling(self, html: str) -> str:
        """Accept historical single-brace placeholders and normalize to {{key}}."""
        keys = (
            "title",
            "subtitle",
            "content",
            "toc_items",
            "message",
            "date_badge",
            "chapter_tag",
            "page_number",
            "total_pages",
        )
        for key in keys:
            html = re.sub(rf"(?<!\{{)\{{\s*{key}\s*\}}(?!\}})", f"{{{{{key}}}}}", html)
            html = re.sub(rf"\{{\{{\s*{key}\s*\}}\}}", f"{{{{{key}}}}}", html)
        return html

    def _ensure_page_content(self, soup, root):
        content_node = root.find("div", class_=lambda c: c and "page-content" in str(c).split())
        if content_node:
            return content_node
        content_node = soup.new_tag("div")
        content_node["class"] = "page-content"
        root.append(content_node)
        return content_node

    def _remove_sample_siblings(self, root, class_names: tuple[str, ...]) -> None:
        """Remove LLM demo content blocks that sit outside the placeholder."""
        for node in list(root.find_all(True, class_=lambda c: c and any(name in str(c).split() for name in class_names))):
            if node.parent is None or node.attrs is None:
                continue
            if "page-content" in str(node.get("class", [])).split():
                continue
            if "{{" in node.get_text("", strip=False):
                continue
            node.decompose()

    def _ensure_footer(self, soup, root) -> None:
        footer = root.find("div", class_=lambda c: c and "slide-footer" in str(c).split())
        if not footer:
            footer = soup.new_tag("div")
            footer["class"] = "slide-footer"
            page_num = soup.new_tag("span")
            page_num["class"] = "page-num"
            page_num.append("{{page_number}}")
            footer.append(page_num)
            root.append(footer)
            return

        page_num = footer.find(class_=lambda c: c and "page-num" in str(c).split())
        if page_num:
            page_num.clear()
            page_num.append("{{page_number}}")

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

    def reload(self) -> None:
        """重新扫描模板目录，加载新增的模板。"""
        self._registry.clear()
        self._load_all_templates()

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
