"""重写 merge_pages_to_document 使用 BeautifulSoup"""
import re
import html as html_lib
from templates.template import Template, PageType


def rewrite_merge_pages_to_document(self, pages, *, document_title="演示文稿", navigation=True):
    """BeautifulSoup 版合并逻辑"""
    from bs4 import BeautifulSoup

    if not pages:
        return ""

    total_pages = len(pages)

    # Build slide containers
    slide_containers = []
    for idx, page_html in enumerate(pages):
        page_num = idx + 1
        container = f'<div class="slide-container"><div class="slide-wrapper" data-page="{page_num}">{page_html}</div></div>'
        slide_containers.append(container)
    slides_inner = "\n".join(slide_containers)

    base_html = self.template.raw_html

    soup = BeautifulSoup(base_html, "html.parser")

    # Find slides-track div
    track = soup.find("div", class_=lambda c: c and "slides-track" in c.split())
    if track:
        # Remove all child elements that are skeleton slides (class="slide ...")
        for slide in track.find_all("div", class_=lambda c: c and "slide" in c.split()):
            slide.decompose()
        # Remove HTML comment nodes
        for comment in list(track.children):
            if hasattr(comment, 'name') and comment.name is None:  # NavigableString/Comment
                comment.extract()
        # Remove non-slide child divs (decorations, etc.)
        for child in list(track.children):
            if hasattr(child, 'name') and child.name == "div":
                child.extract()
        # Inject rendered pages
        pages_soup = BeautifulSoup(slides_inner, "html.parser")
        for child in list(pages_soup.find_all("div", recursive=False)):
            track.append(child)

    # Replace TOTAL_PAGES
    base_html = str(soup)
    base_html = base_html.replace("{{TOTAL_PAGES}}", str(total_pages))
    base_html = base_html.replace("{TOTAL_PAGES}", str(total_pages))
    base_html = base_html.replace("<title>PPT Template</title>", f"<title>{html_lib.escape(document_title)}</title>")

    if not navigation:
        base_html = re.sub(r'<div class="nav-dots"[^>]*></div>', '', base_html)
        base_html = base_html.replace('<div class="nav-arrows">', '<div class="nav-arrows" style="display:none">')

    return base_html


# Monkey-patch
from templates.renderer import TemplateRenderer
TemplateRenderer.merge_pages_to_document = rewrite_merge_pages_to_document
