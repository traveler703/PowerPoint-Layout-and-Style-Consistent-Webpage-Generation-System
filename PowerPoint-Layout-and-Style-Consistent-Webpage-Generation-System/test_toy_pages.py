#!/usr/bin/env python3
"""
Toy 模板一页一页测试：
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
    print("Toy 模板一页一页测试")
    print("=" * 60)

    # 用 LLM client 初始化生成器
    try:
        client = default_llm_client()
        has_llm = "Stub" not in type(client).__name__
    except Exception as e:
        print(f"LLM 初始化失败: {e}")
        return

    if not has_llm or not client:
        print("无 LLM 客户端")
        return

    generator = PresentationGenerator(template_name="toy", llm_client=client)
    await generator.initialize()

    outline = PresentationOutline(
        title="恐龙世界探险",
        subtitle="和小恐龙一起探索远古时代",
        date_badge="2026年儿童节",
        ending_title="探险结束",
        ending_message="下次再见，小探险家们！",
        sections=[
            SectionInput(
                title="认识恐龙",
                content_pages=[
                    ContentPageInput(
                        title="什么是恐龙",
                        summary="恐龙是生活在远古时代的巨型爬行动物，它们在地球上生存了1.6亿年。",
                        bullet_points=[
                            "恐龙生活在距今2.3亿年前的三叠纪",
                            "它们是当时地球上最强大的动物",
                            "恐龙的名字意思是「恐怖的蜥蜴」",
                        ],
                    ),
                ],
            ),
            SectionInput(
                title="恐龙分类",
                content_pages=[
                    ContentPageInput(
                        title="食草恐龙",
                        summary="食草恐龙体型巨大，性格温和，以植物为食。",
                        bullet_points=[
                            "腕龙：长颈鹿般的巨型恐龙",
                            "三角龙：头上有三只角的恐龙",
                            "甲龙：全身披满盔甲的坦克龙",
                        ],
                    ),
                    ContentPageInput(
                        title="食肉恐龙",
                        summary="食肉恐龙行动敏捷，牙齿锋利，是恐龙时代的顶级猎手。",
                        bullet_points=[
                            "霸王龙：已知最强的陆地捕食者",
                            "迅猛龙：聪明敏捷的小型猎手",
                            "棘龙：体型最大的肉食恐龙",
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

    # 调用 pipeline 生成完整演示文稿
    result = await generator.generate_presentation(
        outline=outline,
        output_filename="toy_test.html",
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
