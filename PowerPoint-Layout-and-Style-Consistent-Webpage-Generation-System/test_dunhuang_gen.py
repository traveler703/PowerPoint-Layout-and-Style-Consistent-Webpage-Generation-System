#!/usr/bin/env python3
"""
生成敦煌飞天模板 -> 测试 pipeline
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from generator.llm_client import default_llm_client
from scripts.template_generator import TemplateGenerator
from pipeline import PresentationGenerator, PresentationOutline, SectionInput, ContentPageInput


TEMPLATE_ID = "dunhuang_xi"
TEMPLATE_NAME = "敦煌·丝路"


async def generate_template():
    print("=" * 60)
    print("第1步：生成敦煌飞天模板（跳过，直接使用已有模板）")
    print("=" * 60)
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "data", "user_generated")
    output_path = os.path.join(data_dir, f"{TEMPLATE_ID}.json")
    with open(output_path, encoding="utf-8") as f:
        tpl = json.load(f)
    tpl["template_id"] = TEMPLATE_ID
    tpl["template_name"] = TEMPLATE_NAME
    print(f"已加载: {output_path}")
    print(f"  模板ID: {tpl.get('template_id')}")
    print(f"  模板名: {tpl.get('template_name')}")
    print(f"  页面类型: {', '.join(tpl.get('page_types', {}).keys())}")
    print(f"  raw_html长度: {len(tpl.get('raw_html', ''))}")
    return tpl


async def run_pipeline():
    print("\n" + "=" * 60)
    print("第2步：Pipeline 测试")
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

    generator = PresentationGenerator(template_name=TEMPLATE_ID, llm_client=client)
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
        output_filename="dunhuang_xi_test.html",
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


async def main():
    tpl = await generate_template()
    if tpl:
        await run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
