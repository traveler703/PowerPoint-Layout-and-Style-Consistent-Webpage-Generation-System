#!/usr/bin/env python3
"""对比 toy vs dunhuang 模板的渲染差异"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from templates.template_loader import load_template
from templates.renderer import TemplateRenderer


def test_template(template_id: str):
    print(f"\n{'='*60}")
    print(f"测试模板: {template_id}")
    print('='*60)

    tpl = load_template(template_id)
    if tpl is None:
        print(f"  模板 '{template_id}' 未找到!")
        return

    renderer = TemplateRenderer(tpl)
    print(f"  名称: {tpl.name}")
    print(f"  page_types: {list(tpl.page_types.keys())}")
    print(f"  CSS变量: {tpl.css_variables}")

    # 检查关键 page_types
    for pt in ["cover", "content", "toc", "section", "ending"]:
        cfg = tpl.get_page_type_config(pt)
        if cfg:
            print(f"\n  [{pt}] skeleton:")
            print(f"    {cfg.skeleton[:200]}")
        else:
            print(f"\n  [{pt}] -- 不存在 (fallback)")

    # 测试 section 页面渲染
    print(f"\n  --- Section 页面渲染测试 ---")
    section_html = renderer.render_page(
        page_type="section",
        title="第I章",
        subtitle="认识恐龙",
        page_number=3,
        total_pages=8,
    )
    print(f"  渲染结果 (前300字符):")
    print(f"  {section_html[:300]}")
    if "{{section_num}}" in section_html:
        print(f"  [BUG] {{section_num}} 未被替换!")
    if "{{date_badge}}" in section_html:
        print(f"  [BUG] {{date_badge}} 未被替换!")
    if "{{subtitle}}" in section_html:
        print(f"  [BUG] {{subtitle}} 未被替换!")

    # 测试 cover 页面
    print(f"\n  --- Cover 页面渲染测试 ---")
    cover_html = renderer.render_cover_page(
        title="恐龙世界探险",
        subtitle="和小恐龙一起探索远古时代",
        date_badge="2026年儿童节",
        page_number=1,
        total_pages=8,
    )
    print(f"  渲染结果 (前300字符):")
    print(f"  {cover_html[:300]}")
    if "{{date_badge}}" in cover_html:
        print(f"  [BUG] {{date_badge}} 未被替换!")
    if "{{subtitle}}" in cover_html:
        print(f"  [BUG] {{subtitle}} 未被替换!")

    # 测试 content 页面
    print(f"\n  --- Content 页面渲染测试 ---")
    content_html = renderer.render_content_page(
        title="什么是恐龙",
        content="<div>测试内容</div>",
        page_number=4,
        total_pages=8,
    )
    print(f"  渲染结果 (前300字符):")
    print(f"  {content_html[:300]}")

    # 测试 ending 页面
    print(f"\n  --- Ending 页面渲染测试 ---")
    ending_html = renderer.render_ending_page(
        title="探险结束",
        content="下次再见，小探险家们！",
        page_number=8,
        total_pages=8,
    )
    print(f"  渲染结果 (前300字符):")
    print(f"  {ending_html[:300]}")
    if "{{message}}" in ending_html:
        print(f"  [BUG] {{message}} 未被替换!")
    if "{{emoji}}" in ending_html:
        print(f"  [BUG] {{emoji}} 未被替换!")

    # 检查 raw_html 中的 {{SLIDES_CONTENT}}
    print(f"\n  --- raw_html 检查 ---")
    if "{{SLIDES_CONTENT}}" in tpl.raw_html:
        print(f"  raw_html 包含 {{SLIDES_CONTENT}} ✓")
    else:
        print(f"  [严重BUG] raw_html 缺少 {{SLIDES_CONTENT}} !!")


if __name__ == "__main__":
    # 先列出所有可用模板
    from templates.template_loader import get_loader
    loader = get_loader()
    templates = loader.list_templates()
    print(f"可用模板: {[t.template_id for t in templates]}")

    test_template("toy")
    test_template("dunhuang_xi")
    test_template("ink")
