"""
将 template JSON 渲染为可浏览的 HTML 预览。
"""
import json, pathlib, sys, re

# ─── 从 template_generator 导入构建函数 ─────────────────────────
import sys as _sys
_proj = pathlib.Path(__file__).parent
_sys.path.insert(0, str(_proj))
try:
    from scripts.template_generator import build_raw_html
except ImportError:
    build_raw_html = None


# 每个 page_type 的默认占位内容
DEFAULT_CONTENT = {
    "title":       "演示文稿",
    "subtitle":    "演示文稿副标题",
    "content":     "<h2>第一章：开篇</h2><p>这里是内容区域，可以放置文字、图片、图表等内容。</p><ul><li>要点一：简洁明了</li><li>要点二：重点突出</li><li>要点三：视觉美观</li></ul>",
    "toc_items":   "<div class='toc-item'><div class='toc-number'>01</div><div class='toc-text'><h3>第一章</h3><p>开篇</p></div></div><div class='toc-item'><div class='toc-number'>02</div><div class='toc-text'><h3>第二章</h3><p>发展</p></div></div><div class='toc-item'><div class='toc-number'>03</div><div class='toc-text'><h3>第三章</h3><p>高潮</p></div></div>",
    "date_badge":  "2024",
    "message":     "感谢观看",
    "category":    "默认分类",
    "section_num": "一",
    "page_number": "1",
}


def render_template(template: dict) -> str:
    """
    给定完整 template JSON，返回可独立浏览的 HTML 字符串。
    """
    page_types = template.get("page_types", {})

    if not template.get("raw_html"):
        if build_raw_html is None:
            raise RuntimeError("template_generator 模块不可用，无法构建 raw_html")
        template = build_raw_html(template)

    raw_html = template["raw_html"]

    # 无 {SLIDES_CONTENT} → 直接替换双花括号占位符
    if "{SLIDES_CONTENT}" not in raw_html:
        html = raw_html
        for key, val in DEFAULT_CONTENT.items():
            html = re.sub(r"\{\{" + re.escape(key) + r"\}\}", val, html)
        return html

    def fill_skeleton(skeleton: str) -> str:
        result = skeleton
        for key, val in DEFAULT_CONTENT.items():
            result = re.sub(r"\{\{" + re.escape(key) + r"\}\}", val, result)
        return result

    page_order = ["cover", "content", "toc", "section", "ending",
                  "compare", "chart", "qa", "timeline"]

    # 构建每页的 HTML（不含外层 container，container 由注入逻辑添加）
    filled_slides = []
    for ptype in page_order:
        if ptype not in page_types:
            continue
        sk = page_types[ptype].get("skeleton", "").strip()
        if not sk:
            continue
        filled = fill_skeleton(sk)
        filled_slides.append(filled)

    count = len(filled_slides)

    # 把 slides 注入 raw_html
    html = _inject_slides(raw_html, filled_slides)

    html = re.sub(r"\{\{TOTAL_PAGES\}\}", str(count), html)
    html = re.sub(r"\{\{totalPages\}\}", str(count), html)
    return html


def _inject_slides(raw_html: str, filled_slides: list) -> str:
    """
    将填充好的 slide HTML 列表注入到 raw_html 的 slides-track 中。
    导航按钮保持在 slides-wrapper 层级（固定不动），slides-track 只包含幻灯片。
    """
    # 找到 slides-wrapper 和 slides-track
    wrapper_start = raw_html.find('<div class="slides-wrapper"')
    track_start = raw_html.find('<div class="slides-track"')
    nav_dots_pos = raw_html.find('<div class="nav-dots"')
    if wrapper_start == -1 or track_start == -1 or nav_dots_pos == -1:
        return raw_html.replace("{SLIDES_CONTENT}", _build_slides_html(filled_slides))

    # slides-track 闭合标签（在 nav-dots 之前）
    track_close = raw_html.rfind('</div>', track_start, nav_dots_pos)
    if track_close == -1:
        return raw_html.replace("{SLIDES_CONTENT}", _build_slides_html(filled_slides))

    # slides-track 开放标签
    open_tag_end = raw_html.find('>', track_start) + 1
    open_tag = raw_html[track_start:open_tag_end]

    # 提取 nav arrows（从 slides-track 内部移到 slides-wrapper 层级）
    nav_prev = _extract_tag(raw_html, track_start, 'nav-arrow prev')
    nav_next = _extract_tag(raw_html, track_start, 'nav-arrow next')

    # 重建 slides-track 内部（只放 slides，不含 nav arrows）
    slides_inner = "\n" + _build_slides_html(filled_slides, indent="") + "\n"
    close_tag = raw_html[track_close:track_close + 6]

    # 重组 slides-track
    before_track = raw_html[:track_start]
    after_track_close = raw_html[track_close + 6:]
    track_html = open_tag + slides_inner + close_tag

    # nav arrows 移到 slides-wrapper 层级（在 slides-track 之后）
    nav_html = ""
    if nav_prev:
        nav_html += "\n    " + nav_prev
    if nav_next:
        nav_html += "\n    " + nav_next

    # slides-wrapper 闭合标签
    wrapper_close_pos = raw_html.find('</div>', nav_dots_pos)
    if wrapper_close_pos != -1:
        wrapper_close = raw_html[wrapper_close_pos:wrapper_close_pos + 6]
        before_wrapper_close = raw_html[wrapper_close_pos + 6:]
        new_html = (
            raw_html[:wrapper_start]
            + raw_html[wrapper_start:track_start]
            + track_html
            + nav_html
            + "\n"
            + raw_html[nav_dots_pos:wrapper_close_pos + 6]
            + wrapper_close
            + before_wrapper_close
        )
    else:
        new_html = before_track + track_html + nav_html + after_track_close

    # 清理注释残留
    new_html = re.sub(r'\s*<!--\s*\{SLIDES_CONTENT\}\s*-->\s*\n', '\n', new_html)

    return new_html


def _extract_tag(html: str, track_start: int, cls: str) -> str | None:
    """提取指定 class 的 div 标签及其内容。"""
    pat = f'<div class="{cls}"'
    start = html.find(pat, track_start)
    if start == -1:
        return None
    close = html.find('</div>', start) + 6
    return html[start:close]


def _build_slides_html(filled_slides: list, indent: str = "") -> str:
    """将填充好的 slide 列表组装成带 container 的 HTML。"""
    parts = []
    for sk in filled_slides:
        parts.append(f'{indent}<div class="slide-container">\n{indent}    {sk}\n{indent}</div>')
    return "\n".join(parts)


def main():
    if len(sys.argv) < 2:
        print("用法: python render_preview.py <模板JSON路径>")
        print("示例: python render_preview.py templates/data/ink.json")
        print("示例: python render_preview.py output/generated_templates/xxx.json")
        sys.exit(1)

    json_path = pathlib.Path(sys.argv[1])
    if not json_path.exists():
        print(f"文件不存在: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    tid   = template.get("template_id", json_path.stem)
    tname = template.get("template_name", tid)
    has_raw = bool(template.get("raw_html"))

    print(f"渲染模板: {tname} ({tid})")
    print(f"page_types: {list(template.get('page_types', {}).keys())}")
    print(f"raw_html: {'有' if has_raw else '无（将自动构建）'}")

    html = render_template(template)

    out_path = json_path.parent / f"{tid}_preview.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"已生成: {out_path}")
    return out_path


if __name__ == "__main__":
    main()
