#!/usr/bin/env python3
"""
敦煌飞天模板测试：
  1. 封面   - render_cover_page
  2. 目录   - render_toc_page
  3. 章节   - render_page(page_type="section")
  4. 内容   - render_content_page (content 由 LLM 两阶段生成)
  5. 结尾   - render_ending_page
  6. 合并   - merge_pages_to_document
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from pipeline import PresentationGenerator, PresentationOutline, SectionInput, ContentPageInput
from generator.llm_client import default_llm_client


async def main():
    print("=" * 60)
    print("敦煌飞天模板测试")
    print("=" * 60)

    try:
        client = default_llm_client()
        has_llm = "Stub" not in type(client).__name__
    except Exception as e:
        print(f"LLM 初始化失败: {e}")
        return

    if not has_llm or not client:
        print("无 LLM 客户端")
        return

    generator = PresentationGenerator(template_name="dunhuang_feitian_v1", llm_client=client)
    await generator.initialize()

    outline = PresentationOutline(
        title="敦煌艺术之旅",
        subtitle="穿越千年丝路 探寻壁画瑰宝",
        date_badge="2026年",
        ending_title="丝路未央",
        ending_message="感谢观看，愿艺术之美永续传承",
        sections=[
            SectionInput(
                title="莫高窟概览",
                content_pages=[
                    ContentPageInput(
                        title="洞窟历史",
                        summary="莫高窟始建于前秦时期，历经千年营造，是中国现存规模最大的石窟艺术宝库。",
                        bullet_points=[
                            "始建于前秦建元二年（公元366年）",
                            "共有735个洞窟，壁画4.5万平方米",
                            "被誉为「东方艺术明珠」",
                        ],
                    ),
                ],
            ),
            SectionInput(
                title="飞天艺术",
                content_pages=[
                    ContentPageInput(
                        title="飞天的起源",
                        summary="飞天是敦煌壁画中最具代表性的艺术形象，源自印度神话中的乾达婆与紧那罗。",
                        bullet_points=[
                            "飞天手持乐器，凌空飞舞",
                            "融合了印度、波斯与中国文化元素",
                            "展现了古代画师的卓越技艺",
                        ],
                    ),
                    ContentPageInput(
                        title="色彩与线条",
                        summary="敦煌壁画以矿物颜料绘制，色彩历经千年仍鲜艳夺目，线条流畅优美。",
                        bullet_points=[
                            "朱砂红为主色调，配以青金石蓝",
                            "采用「凹凸法」渲染立体感",
                            "线条被誉为「吴带当风」",
                        ],
                    ),
                ],
            ),
        ],
    )

    print(f"\n模板: {generator.template.name}")
    print(f"CSS 变量: {generator.template.css_variables}")
    print(f"\n各页类型:")
    total_sections = len(outline.sections)
    total_content = sum(len(s.content_pages) for s in outline.sections)
    total = 1 + 1 + total_sections + total_content + 1
    print(f"  1: cover  封面")
    print(f"  2: toc    目录")
    for i, s in enumerate(outline.sections, 1):
        print(f"  第{2+i}: section 章节 - {s.title}")
        for j, cp in enumerate(s.content_pages, 1):
            print(f"  第{2+i+j}: content 内容 - {cp.title}")
    print(f"  {total}: ending 结尾")

    result = await generator.generate_presentation(
        outline=outline,
        output_filename="dunhuang_test.html",
        navigation=True,
        save_pages=False,
    )

    print(f"\n生成结果:")
    print(f"  成功: {result.success}")
    if result.output_path:
        print(f"  输出: {result.output_path}")
    print(f"  页数: {result.page_count}")
    print(f"  大小: {result.document_size} bytes")
    if result.error:
        print(f"  错误:\n{result.error}")
    print(f"\n各页布局:")
    for layout in result.page_layouts:
        print(f"  {layout}")


if __name__ == "__main__":
    asyncio.run(main())
