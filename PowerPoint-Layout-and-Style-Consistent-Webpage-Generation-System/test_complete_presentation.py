#!/usr/bin/env python3
"""
Test complete presentation generation using:
- Cover page (template)
- TOC page (template)
- Section page (template)
- Content page (two-stage layout generation with LLM)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from engine.types import SemanticPageInput
from templates.template_loader import load_template
from templates.renderer import TemplateRenderer
from generator.prompts import (
    build_layout_analysis_prompt,
    parse_layout_analysis,
    build_html_generation_prompt,
    generate_color_scheme_from_template,
    parse_html_response,
)
from generator.llm_client import default_llm_client


# ============================================================
# Presentation Outline
# ============================================================
PRESENTATION_OUTLINE = {
    "title": "人工智能技术专题",
    "subtitle": "从基础理论到行业应用",
    "date_badge": "2026年度",
    "sections": [
        {
            "title": "人工智能发展史",
            "content_pages": [
                {
                    "title": "图灵时代",
                    "summary": "AI概念萌芽与早期探索",
                    "bullets": [
                        "1950年：图灵发表《计算机器与智能》",
                        "图灵测试：机器能否思考的哲学思考",
                        "1956年：达特茅斯会议，AI正式诞生",
                        "感知机模型：第一个神经网络尝试"
                    ]
                },
                {
                    "title": "专家系统时代",
                    "summary": "知识工程与规则推理",
                    "bullets": [
                        "1960-70年代：专家系统兴起",
                        "DENDRAL、MYCIN等标志性系统",
                        "知识获取瓶颈：专家知识的难以形式化",
                        "1980年代商业化浪潮"
                    ]
                },
                {
                    "title": "深度学习革命",
                    "summary": "从AlexNet到ChatGPT",
                    "bullets": [
                        "2012年：AlexNet突破ImageNet",
                        "GPU并行计算驱动深度学习",
                        "2017年：Transformer架构诞生",
                        "2020年后：大语言模型时代"
                    ]
                }
            ]
        },
        {
            "title": "深度学习核心技术",
            "content_pages": [
                {
                    "title": "卷积神经网络",
                    "summary": "计算机视觉的基石",
                    "bullets": [
                        "局部感受野与权值共享",
                        "LeNet → AlexNet → ResNet演进",
                        "图像分类、目标检测、语义分割",
                        "医疗影像、自动驾驶应用"
                    ]
                },
                {
                    "title": "循环神经网络",
                    "summary": "序列数据处理的专家",
                    "bullets": [
                        "RNN → LSTM → GRU进化",
                        "处理时序数据和文本",
                        "机器翻译、语音识别",
                        "梯度消失问题的解决方案"
                    ]
                },
                {
                    "title": "Transformer架构",
                    "summary": "注意力机制改变一切",
                    "bullets": [
                        "自注意力机制并行计算",
                        "BERT和GPT系列模型",
                        "ChatGPT：对话AI的突破",
                        "多模态融合：GPT-4V"
                    ]
                }
            ]
        },
        {
            "title": "AI应用场景全景",
            "content_pages": [
                {
                    "title": "计算机视觉",
                    "summary": "机器之眼的进化",
                    "bullets": [
                        "人脸识别：安防与支付",
                        "自动驾驶：感知与决策",
                        "医学影像：辅助诊断",
                        "工业检测：质量控制"
                    ]
                },
                {
                    "title": "自然语言处理",
                    "summary": "人机交互的革新",
                    "bullets": [
                        "机器翻译：打破语言障碍",
                        "智能客服：7x24服务",
                        "内容生成：写作与创作",
                        "知识图谱：信息组织"
                    ]
                },
                {
                    "title": "科学计算",
                    "summary": "AI for Science",
                    "bullets": [
                        "AlphaFold：蛋白质结构预测",
                        "气候模拟：天气预报",
                        "材料发现：新药研发",
                        "核聚变控制：能源革命"
                    ]
                }
            ]
        }
    ]
}


# ============================================================
# Page Generation Functions
# ============================================================
async def generate_content_page_html(
    client,
    page: SemanticPageInput,
    colors: dict
) -> str:
    """Generate HTML for a content page using two-stage method."""
    # Stage 1: Layout expert analysis
    sys_prompt, user_prompt = build_layout_analysis_prompt(page)
    response = await client.complete(sys_prompt, user_prompt)
    layout_analysis = parse_layout_analysis(response)

    print(f"      布局类型: {layout_analysis['layout_type']}")

    # Stage 2: HTML generation
    sys_prompt, user_prompt = build_html_generation_prompt(
        page=page,
        layout_analysis=layout_analysis,
        colors=colors,
    )
    response = await client.complete(sys_prompt, user_prompt)
    html = parse_html_response(response)

    return html


# ============================================================
# Main Generation
# ============================================================
async def main():
    print("=" * 70)
    print("Complete Presentation Generation Test")
    print("Cover + TOC + Sections + Content (Two-Stage Layout)")
    print("=" * 70)

    # Load template
    template = load_template("tech")
    renderer = TemplateRenderer(template)
    colors = generate_color_scheme_from_template(template.css_variables)

    print(f"\n[INFO] Template: {template.name}")
    print(f"[INFO] Primary color: {colors['THEME_COLOR']}")

    # Get LLM client
    try:
        client = default_llm_client()
        has_llm = "Stub" not in type(client).__name__
    except Exception as e:
        print(f"LLM client error: {e}")
        return

    if not has_llm or not client:
        print("No LLM client available")
        return

    pages = []
    page_number = 1
    total_sections = len(PRESENTATION_OUTLINE["sections"])
    total_content_pages = sum(
        len(s["content_pages"]) for s in PRESENTATION_OUTLINE["sections"]
    )
    total_pages = 1 + 1 + total_sections + total_content_pages  # cover + toc + sections + content

    # ============================================================
    # Page 1: Cover
    # ============================================================
    print(f"\n[{page_number}/{total_pages}] Rendering cover page...")
    cover_page = renderer.render_cover_page(
        title=PRESENTATION_OUTLINE["title"],
        subtitle=PRESENTATION_OUTLINE["subtitle"],
        date_badge=PRESENTATION_OUTLINE["date_badge"],
        page_number=page_number,
        total_pages=total_pages,
    )
    pages.append(cover_page)
    print(f"      ✓ {PRESENTATION_OUTLINE['title']}")
    page_number += 1

    # ============================================================
    # Page 2: TOC
    # ============================================================
    print(f"\n[{page_number}/{total_pages}] Rendering TOC page...")
    toc_items = [
        {"title": s["title"], "description": f"{len(s['content_pages'])} 页内容"}
        for s in PRESENTATION_OUTLINE["sections"]
    ]
    toc_page = renderer.render_toc_page(
        title="目录",
        toc_items=toc_items,
        page_number=page_number,
        total_pages=total_pages,
    )
    pages.append(toc_page)
    print(f"      ✓ 目录 - {len(toc_items)} 个章节")
    page_number += 1

    # ============================================================
    # Sections and Content Pages
    # ============================================================
    for section_idx, section in enumerate(PRESENTATION_OUTLINE["sections"], 1):
        section_title = section["title"]

        # Section Page
        print(f"\n[{page_number}/{total_pages}] Rendering section page...")
        section_page = renderer.render_page(
            page_type="cover",
            title=f"第{roman_numeral(section_idx)}章",
            subtitle=section_title,
            page_number=page_number,
            total_pages=total_pages,
        )
        pages.append(section_page)
        print(f"      ✓ {section_title}")
        page_number += 1

        # Content Pages
        for content_page in section["content_pages"]:
            print(f"\n[{page_number}/{total_pages}] Generating content page...")
            print(f"      标题: {content_page['title']}")

            semantic_page = SemanticPageInput(
                page_index=len(pages),
                title=content_page["title"],
                summary=content_page["summary"],
                page_type="content",
                bullet_points=content_page["bullets"],
            )

            html_content = await generate_content_page_html(client, semantic_page, colors)

            content_page_rendered = renderer.render_content_page(
                title=content_page["title"],
                content=html_content,
                bullets=None,  # HTML already contains all content
                page_number=page_number,
                total_pages=total_pages,
            )
            pages.append(content_page_rendered)
            print(f"      ✓ 生成完成")
            page_number += 1

    # ============================================================
    # Merge and Save
    # ============================================================
    print("\n" + "=" * 70)
    print("[MERGE] Merging all pages...")

    document = renderer.merge_pages_to_document(
        pages=pages,
        document_title=PRESENTATION_OUTLINE["title"],
        navigation=True,
    )

    output_path = os.path.join(
        os.path.dirname(__file__),
        "output",
        "test_complete_presentation.html"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(document)

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 70)
    print("[DONE] Complete presentation generated!")
    print(f"[INFO] Output: {output_path}")
    print(f"[INFO] Total pages: {len(pages)}")
    print(f"[INFO] Document size: {len(document):,} chars")
    print("=" * 70)

    # Page breakdown
    print("\n[Page Breakdown]")
    print("-" * 50)
    print(f"| {'#':<3} | {'Type':<12} | {'Title':<30} |")
    print("-" * 50)

    p_num = 1
    print(f"| {p_num:<3} | {'Cover':<12} | {PRESENTATION_OUTLINE['title']:<30} |")
    p_num += 1
    print(f"| {p_num:<3} | {'TOC':<12} | {'目录':<30} |")
    p_num += 1

    for sec_idx, section in enumerate(PRESENTATION_OUTLINE["sections"], 1):
        print(f"| {p_num:<3} | {'Section':<12} | {section['title']:<30} |")
        p_num += 1
        for content in section["content_pages"]:
            print(f"| {p_num:<3} | {'Content':<12} | {content['title']:<30} |")
            p_num += 1

    print("-" * 50)


def roman_numeral(num: int) -> str:
    """Convert number to Roman numeral."""
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syms = [
        'M', 'CM', 'D', 'CD',
        'C', 'XC', 'L', 'XL',
        'X', 'IX', 'V', 'IV',
        'I'
    ]
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num


if __name__ == "__main__":
    asyncio.run(main())
