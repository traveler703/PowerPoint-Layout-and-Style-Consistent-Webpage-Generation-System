"""Template renderer for filling placeholders and merging pages."""

from __future__ import annotations

import re
import html as html_lib
from typing import Any

from templates.template import Template, PageType, PageTypeConfig


class TemplateRenderer:
    """Renders content into template placeholders."""

    def __init__(self, template: Template) -> None:
        self.template = template

    def _inject_runtime_overrides(self, html: str) -> str:
        """Add safety CSS that keeps generated content inside the template canvas."""
        css = """
<style id="landppt-runtime-overrides">
html,body{width:100%!important;height:100%!important;min-width:0!important;min-height:0!important;overflow:hidden!important;}
body{display:flex!important;align-items:center!important;justify-content:center!important;margin:0!important;padding:0!important;}
#slidesWrapper,.slides-wrapper{width:1280px!important;height:720px!important;min-width:1280px!important;min-height:720px!important;flex:0 0 1280px!important;transform-origin:center center!important;}
#slidesTrack,.slides-track{width:1280px!important;height:720px!important;min-width:1280px!important;min-height:720px!important;}
.slide .page-content{overflow:hidden;}
.slide .page-content.allow-scroll{overflow:auto;scrollbar-width:thin;}
.slide .page-content::-webkit-scrollbar{width:6px;height:6px;}
.slide .page-content::-webkit-scrollbar-thumb{border-radius:10px;background:rgba(148,163,184,.45);}
.slide .page-content .generated-toc{max-height:100%;overflow:hidden!important;padding:4px!important;box-sizing:border-box!important;}
.slide.toc .page-content .generated-toc{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:16px 22px!important;align-content:center!important;width:100%!important;height:100%!important;}
.slide.toc .page-content .generated-toc .toc-item{display:flex!important;align-items:center!important;gap:14px!important;width:auto!important;min-width:0!important;min-height:0!important;margin:0!important;padding:14px 18px!important;border-radius:22px!important;background:#fff!important;border:1px solid rgba(255,127,63,.18)!important;border-left:6px solid var(--color-primary,#FF7F3F)!important;box-shadow:0 8px 22px rgba(255,127,63,.08)!important;box-sizing:border-box!important;}
.slide.toc .page-content .generated-toc .toc-number{display:flex!important;align-items:center!important;justify-content:center!important;width:48px!important;height:48px!important;flex:0 0 48px!important;border-radius:999px!important;background:rgba(255,127,63,.10)!important;color:var(--color-primary,#FF7F3F)!important;font-weight:800!important;font-size:18px!important;}
.slide .page-content .generated-toc .toc-text{min-width:0!important;overflow:hidden!important;}
.slide .page-content .generated-toc .toc-text h3{font-size:clamp(15px,1.55vw,20px)!important;line-height:1.35!important;margin:0!important;white-space:normal!important;overflow-wrap:anywhere!important;color:var(--color-text,#2D3436)!important;}
.slide .page-content .generated-toc .toc-text p:empty{display:none!important;}
.slide .page-content .generated-toc .toc-text p{font-size:12px!important;line-height:1.35!important;margin:4px 0 0!important;color:var(--color-text-muted,#6B7280)!important;}
.slide.cover > h1:not(.main-title){position:absolute!important;left:80px!important;right:80px!important;top:190px!important;margin:0!important;font-size:clamp(44px,6vw,78px)!important;line-height:1.15!important;color:#fff!important;text-shadow:0 0 36px rgba(96,165,250,.38)!important;z-index:20!important;}
.slide.cover > .subtitle{color:rgba(224,242,254,.9)!important;z-index:20!important;}
.slides-track > .slide-container,
.slides-track > .slide-container > .slide-wrapper{width:1280px!important;height:720px!important;min-width:1280px!important;min-height:720px!important;flex:0 0 1280px!important;}
.slides-track > .slide-container > .slide-wrapper > .slide{width:1280px!important;height:720px!important;min-width:1280px!important;min-height:720px!important;}
.slide .page-content .slide,
.slide .page-content .slides-wrapper,
.slide .page-content .slide-container,
.slide .page-content .slide-wrapper{width:100%!important;height:100%!important;min-width:0!important;min-height:0!important;box-shadow:none!important;border-radius:0!important;background:transparent!important;}
</style>
<script id="landppt-runtime-fixes">
(function(){
  function fixPageCount(){
    var track=document.getElementById('slidesTrack');
    var total=track ? track.querySelectorAll(':scope > .slide-container, :scope > .slide').length : document.querySelectorAll('.slide').length;
    var totalEl=document.getElementById('totalPages');
    if(totalEl && total) totalEl.textContent=String(total);
    window.__totalSlides=total;
  }
  function fitPresentation(){
    var wrapper=document.getElementById('slidesWrapper') || document.querySelector('.slides-wrapper');
    if(!wrapper) return;
    var scale=Math.min(window.innerWidth / 1280, window.innerHeight / 720, 1);
    wrapper.style.setProperty('transform','scale(' + scale + ')','important');
    wrapper.style.setProperty('transform-origin','center center','important');
  }
  function initializeRuntime(){
    fixPageCount();
    fitPresentation();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',initializeRuntime);
  else initializeRuntime();
  window.addEventListener('load',fitPresentation);
  window.addEventListener('resize',fitPresentation);
})();
</script>
"""
        if "landppt-runtime-overrides" in html:
            return html
        if "</head>" in html:
            return html.replace("</head>", css + "\n</head>", 1)
        return css + html

    def render_page(
        self,
        page_type: str,
        *,
        title: str = "",
        subtitle: str = "",
        content: str = "",
        bullets: list[str] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
        extra: dict[str, Any] | None = None,
    ) -> str:
        page_config = self.template.get_page_type_config(page_type)

        if page_config is None:
            if page_type == "section":
                page_config = self._create_section_fallback_config()
            if page_config is None:
                return self._render_default_page(
                    page_type=page_type,
                    title=title,
                    content=content,
                    bullets=bullets,
                    page_number=page_number,
                    total_pages=total_pages,
                )

        placeholders = {
            "title": html_lib.escape(title) if title else "",
            "subtitle": html_lib.escape(subtitle) if subtitle else "",
            "content": content,
            "bullets": self._render_bullets(bullets or []),
            "page_number": str(page_number),
            "total_pages": str(total_pages),
            "page_type": page_type,
        }

        if extra:
            for key, value in extra.items():
                placeholders[key] = str(value)

        rendered = page_config.skeleton
        for key, value in placeholders.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))

        return rendered

    def render_cover_page(
        self,
        title: str,
        subtitle: str = "",
        date_badge: str = "",
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        return self.render_page(
            page_type=PageType.COVER,
            title=title,
            subtitle=subtitle,
            extra={"date_badge": date_badge},
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_content_page(
        self,
        title: str,
        content: str = "",
        bullets: list[str] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        return self.render_page(
            page_type=PageType.CONTENT,
            title=title,
            content=content,
            bullets=bullets,
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_toc_page(
        self,
        title: str,
        toc_items: list[dict[str, str]] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        toc_html = self._render_toc_items(toc_items or [])
        return self.render_page(
            page_type=PageType.TOC,
            title=title,
            extra={"toc_items": toc_html},
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_ending_page(
        self,
        title: str = "谢谢观看",
        content: str = "",
        emoji: str = "",
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        return self.render_page(
            page_type=PageType.ENDING,
            title=title,
            content="",
            extra={
                "emoji": emoji,
                "message": content,
            },
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_comparison_page(
        self,
        title: str,
        items: list[dict[str, Any]] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        items_html = self._render_comparison_items(items or [])
        return self.render_page(
            page_type=PageType.COMPARE,
            title=title,
            extra={"items": items_html},
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_timeline_page(
        self,
        title: str,
        timeline_items: list[dict[str, str]] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        timeline_html = self._render_timeline_items(timeline_items or [])
        return self.render_page(
            page_type=PageType.TIMELINE,
            title=title,
            extra={"timeline_items": timeline_html},
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_qa_page(
        self,
        title: str,
        qa_items: list[dict[str, str]] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        qa_html = self._render_qa_items(qa_items or [])
        return self.render_page(
            page_type=PageType.QA,
            title=title,
            extra={"qa_items": qa_html},
            page_number=page_number,
            total_pages=total_pages,
        )

    def merge_pages_to_document(
        self,
        pages: list[str],
        *,
        document_title: str = "演示文稿",
        navigation: bool = True,
    ) -> str:
        if not pages:
            return ""

        total_pages = len(pages)

        # Build slide containers
        slide_containers = []
        for idx, page_html in enumerate(pages):
            page_num = idx + 1
            container = (
                f'<div class="slide-container">'
                f'<div class="slide-wrapper" data-page="{page_num}">{page_html}</div>'
                f'</div>'
            )
            slide_containers.append(container)
        slides_inner = "".join(slide_containers)

        base_html = self.template.raw_html

        # Try BeautifulSoup for robust HTML manipulation
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            base_html = base_html.replace("{{SLIDES_CONTENT}}", slides_inner)
            base_html = base_html.replace("{SLIDES_CONTENT}", slides_inner)
            base_html = base_html.replace("{{TOTAL_PAGES}}", str(total_pages))
            base_html = base_html.replace("{TOTAL_PAGES}", str(total_pages))
            base_html = base_html.replace("<title>PPT Template</title>", f"<title>{html_lib.escape(document_title)}</title>")
            if not navigation:
                base_html = re.sub(r'<div class="nav-dots"[^>]*></div>', '', base_html)
                base_html = base_html.replace('<div class="nav-arrows">', '<div class="nav-arrows" style="display:none">')
            return self._inject_runtime_overrides(base_html)

        soup = BeautifulSoup(base_html, "html.parser")

        # Find slides-track
        track = soup.find("div", class_=lambda c: c and "slides-track" in c.split())
        if track:
            # 只删除 slides-track 的直接子元素中属于示例 slide 的部分
            # 不递归删除（避免把 slide-container / slide-wrapper 也删掉）
            for child in list(track.children):
                if not hasattr(child, 'name') or child.name != 'div':
                    continue
                child_class = child.get('class', [])
                child_class_str = ' '.join(child_class) if isinstance(child_class, list) else str(child_class)
                # 只删除直接的示例 slide div（不是 slide-container / slide-wrapper）
                is_example_slide = (
                    'slide' in child_class_str.split()
                    and 'container' not in child_class_str
                    and 'wrapper' not in child_class_str
                )
                if is_example_slide:
                    # 删除示例 slide 内部的 footer（避免合并后出现两套 footer）
                    for footer in child.find_all("div", class_=lambda c: c and 'slide-footer' in c.split()):
                        footer.decompose()
                    child.decompose()
            # 移除 track 内的文本节点/注释
            for child in list(track.children):
                if hasattr(child, 'name') and child.name is None:
                    child.extract()
            # 注入渲染后的页面
            pages_soup = BeautifulSoup(slides_inner, "html.parser")
            for child in list(pages_soup.find_all("div", recursive=False)):
                track.append(child)

        base_html = str(soup)
        base_html = base_html.replace("{{TOTAL_PAGES}}", str(total_pages))
        base_html = base_html.replace("{TOTAL_PAGES}", str(total_pages))
        base_html = base_html.replace("<title>PPT Template</title>", f"<title>{html_lib.escape(document_title)}</title>")

        if not navigation:
            base_html = re.sub(r'<div class="nav-dots"[^>]*></div>', '', base_html)
            base_html = base_html.replace('<div class="nav-arrows">', '<div class="nav-arrows" style="display:none">')

        return self._inject_runtime_overrides(base_html)

    def _render_default_page(
        self,
        page_type: str,
        title: str,
        content: str,
        bullets: list[str] | None,
        page_number: int,
        total_pages: int,
    ) -> str:
        bullets_html = self._render_bullets(bullets or [])
        combined_content = f"{content}\n{bullets_html}" if content else bullets_html

        return (
            f'<div class="slide {page_type}">'
            f'<div class="page-title">{html_lib.escape(title)}</div>'
            f'<div class="page-content">{combined_content}</div>'
            f'<div class="slide-footer">'
            f'<span class="page-num">{page_number}</span>'
            f'</div>'
            f'</div>'
        )

    def _create_section_fallback_config(self) -> "PageTypeConfig":
        """Create a proper section page skeleton from template CSS variables.

        When a template lacks a section page type, generate one that inherits
        the template's color scheme and typography, instead of falling back to
        the cover page which has completely different semantics.
        """
        css = self.template.css_variables or {}
        bg = css.get("color-background", "#0a0a0a")
        text = css.get("color-text", "#e0e0e0")
        accent = css.get("color-accent", css.get("color-primary", "#6366f1"))
        muted = css.get("color-text-muted", "#888")
        heading_font = css.get("font-heading", css.get("font-body", "sans-serif"))

        skeleton = (
            f'<div class="slide section" style="background:{bg};color:{text};'
            'position:relative;overflow:hidden;width:1280px;height:720px;">'
            f'<div class="page-title" style="position:absolute;top:60px;left:80px;'
            f'font-size:18px;color:{accent};letter-spacing:6px;text-transform:uppercase;">'
            '{{chapter_tag}}</div>'
            f'<h1 class="section-title" style="position:absolute;top:50%;left:50%;'
            'transform:translate(-50%,-50%);margin:0;'
            f'font-family:{heading_font};font-size:52px;color:{text};'
            'font-weight:700;text-align:center;line-height:1.3;width:80%;">'
            '{{title}}</h1>'
            f'<p class="subtitle" style="position:absolute;top:calc(50% + 80px);'
            'left:50%;transform:translateX(-50%);margin:0;'
            f'font-size:20px;color:{muted};">'
            '{{subtitle}}</p>'
            '<div class="slide-footer" style="position:absolute;bottom:15px;'
            'left:0;right:0;text-align:center;">'
            '<span class="page-num">{{page_number}}</span>'
            '</div>'
            '</div>'
        )
        return PageTypeConfig(
            type_name=PageType.SECTION,
            skeleton=skeleton,
            placeholders=["chapter_tag", "title", "subtitle", "page_number"],
        )

    def _render_bullets(self, bullets: list[str]) -> str:
        if not bullets:
            return ""
        items = []
        for bullet in bullets:
            escaped = html_lib.escape(bullet)
            items.append(f"<li>{escaped}</li>")
        return f"<ul>{''.join(items)}</ul>"

    def _render_toc_items(self, items: list[dict[str, str]]) -> str:
        if not items:
            return ""
        html_parts = []
        for idx, item in enumerate(items, 1):
            number = f"{idx:02d}"
            title_esc = html_lib.escape(item.get("title", ""))
            desc_esc = html_lib.escape(item.get("description", ""))
            html_parts.append(
                f'<div class="toc-item">'
                f'<div class="toc-number">{number}</div>'
                f'<div class="toc-text"><h3>{title_esc}</h3><p>{desc_esc}</p></div>'
                f'</div>'
            )
        return f'<div class="generated-toc">{"".join(html_parts)}</div>'

    def _render_comparison_items(self, items: list[dict[str, Any]]) -> str:
        if not items:
            return ""
        html_parts = []
        for item in items:
            title_esc = html_lib.escape(item.get("title", ""))
            era = item.get("era", "")
            desc_esc = html_lib.escape(item.get("description", ""))
            features = item.get("features", [])
            features_html = "".join(f"<li>{html_lib.escape(f)}</li>" for f in features)
            html_parts.append(
                f'<div class="compare-card">'
                f'<h3>{title_esc}</h3>'
                f'<span class="era">{html_lib.escape(era)}</span>'
                f'<p>{desc_esc}</p>'
                f'<ul>{features_html}</ul>'
                f'</div>'
            )
        return "".join(html_parts)

    def _render_timeline_items(self, items: list[dict[str, str]]) -> str:
        if not items:
            return ""
        html_parts = []
        for item in items:
            title_esc = html_lib.escape(item.get("title", ""))
            desc_esc = html_lib.escape(item.get("description", ""))
            icon = item.get("icon", "●")
            html_parts.append(
                f'<div class="timeline-item">'
                f'<div class="timeline-content"><h3>{icon} {title_esc}</h3><p>{desc_esc}</p></div>'
                f'</div>'
            )
        return "".join(html_parts)

    def _render_qa_items(self, items: list[dict[str, str]]) -> str:
        if not items:
            return ""
        html_parts = []
        for item in items:
            q_esc = html_lib.escape(item.get("question", ""))
            a_esc = html_lib.escape(item.get("answer", ""))
            html_parts.append(
                f'<div class="qa-card">'
                f'<div class="question">{q_esc}</div>'
                f'<div class="answer">{a_esc}</div>'
                f'</div>'
            )
        return "".join(html_parts)

    def _generate_navigation(self, total_pages: int) -> str:
        dots = []
        for i in range(total_pages):
            active = "active" if i == 0 else ""
            dots.append(f'<div class="nav-dot {active}" data-page="{i + 1}"></div>')

        return (
            f'<div class="nav-dots" id="navDots">{"".join(dots)}</div>'
            f'<div class="nav-arrows">'
            f'<div class="nav-arrow" id="prevBtn" onclick="prevSlide()">'
            f'<i class="fa-solid fa-chevron-left"></i></div>'
            f'<div class="nav-arrow" id="nextBtn" onclick="nextSlide()">'
            f'<i class="fa-solid fa-chevron-right"></i></div>'
            f'</div>'
            f'<div class="page-indicator" id="pageIndicator">'
            f'<span class="current" id="currentPage">1</span> / <span id="totalPages">{total_pages}</span>'
            f'</div>'
        )

    def _extract_template_css(self) -> str:
        style_match = re.search(r"<style>(.*?)</style>", self.template.raw_html, re.DOTALL)
        if style_match:
            return style_match.group(1)
        return ""

    def _extract_template_js(self) -> str:
        script_match = re.search(r"<script>(.*?)</script>", self.template.raw_html, re.DOTALL)
        if script_match:
            return script_match.group(1)
        return ""
