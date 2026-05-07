"""
统一模板测试：测试 tech.json、toy.json、gen_1777900164.json 三个模板。

每个模板都走完整流程：
  1. 用 PresentationGenerator 加载模板
  2. 生成一页封面 + 目录 + 章节 + 内容 + 结尾
  3. 输出完整 HTML，验证结构正确
  4. 检查占位符是否全部被替换
"""
import asyncio
import os
import sys
import json
import re
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from pipeline import PresentationGenerator, PresentationOutline, SectionInput, ContentPageInput
from generator.llm_client import DeepSeekChatClient


def make_outline():
    return PresentationOutline(
        title="测试演示文稿",
        subtitle="测试副标题",
        date_badge="2026年",
        ending_title="测试结尾",
        ending_message="这是测试结尾语",
        sections=[
            SectionInput(
                title="第一章",
                content_pages=[
                    ContentPageInput(
                        title="第一节",
                        summary="这是第一节的摘要内容。",
                        bullet_points=["第一点内容", "第二点内容", "第三点内容"],
                    ),
                    ContentPageInput(
                        title="第二节",
                        summary="这是第二节的摘要内容。",
                        bullet_points=["另一个第一点", "另一个第二点"],
                    ),
                ],
            ),
        ],
    )


def strip_scripts(html: str) -> str:
    return re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)


def validate_output(doc_html: str, template_id: str, checks: list[tuple[str, bool]]):
    checks.extend([
        ("HTML 非空", len(doc_html) > 100),
        ("包含 slide div", "<div class=\"slide " in doc_html or "<div class='slide " in doc_html),
        ("包含 nav-dots", "nav-dots" in doc_html),
        ("包含 page-indicator", "page-indicator" in doc_html or "pageIndicator" in doc_html),
        ("封面标题已替换", "测试演示文稿" in doc_html),
        ("内容页有实际内容", "第一节" in doc_html or "第二节" in doc_html),
        ("章节标签已替换", "第I章" in doc_html or "第一章" in doc_html),
        ("包含页码指示器", "page-indicator" in doc_html or "pageIndicator" in doc_html or "totalPages" in doc_html),
    ])

    content_only = strip_scripts(doc_html)
    for ph in ["{{title}}", "{{content}}", "{{chapter_tag}}", "{{subtitle}}",
               "{{message}}"]:
        count = len(re.findall(re.escape(ph), content_only))
        checks.append((f"无残留 {ph}", count == 0))


async def test_template(template_id: str, template_path: str) -> tuple[int, int]:
    print(f"\n{'='*50}")
    print(f"Testing template: {template_id}")
    print(f"{'='*50}")

    client = DeepSeekChatClient(timeout_s=180.0)
    ppt_gen = PresentationGenerator(template_name=template_id, llm_client=client)

    try:
        await ppt_gen.initialize()
    except Exception as e:
        print(f"  加载失败: {e}")
        print(f"  尝试从 JSON 文件直接加载...")
        with open(template_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        from templates.template_loader import TemplateLoader
        loader = TemplateLoader()
        ppt_gen.template = loader._parse_template_data(raw_data)
        from templates.renderer import TemplateRenderer
        ppt_gen.renderer = TemplateRenderer(ppt_gen.template)

    print(f"  模板名: {ppt_gen.template.name}")
    print(f"  page_types: {list(ppt_gen.template.page_types.keys())}")

    outline = make_outline()
    total_sections = len(outline.sections)
    total_content = sum(len(s.content_pages) for s in outline.sections)
    total = 1 + 1 + total_sections + total_content + 1
    print(f"  结构: 1封面 + 1目录 + {total_sections}章节 + {total_content}内容 + 1结尾 = {total} 页")

    t0 = time.time()
    result = await ppt_gen.generate_presentation(
        outline=outline,
        output_filename=f"{template_id}_test.html",
        navigation=True,
        save_pages=True,
    )
    elapsed = time.time() - t0

    print(f"  生成耗时: {elapsed:.1f}s  成功: {result.success}")
    if result.output_path:
        print(f"  输出: {result.output_path}")
    print(f"  页数: {result.page_count}  大小: {result.document_size:,} bytes")

    checks: list[tuple[str, bool]] = []
    checks.append(("生成成功", result.success))

    if result.output_path and os.path.exists(result.output_path):
        with open(result.output_path, "r", encoding="utf-8") as f:
            doc_html = f.read()
        validate_output(doc_html, template_id, checks)
        print(f"  HTML: {len(doc_html):,} 字符")
    else:
        checks.append(("输出文件存在", False))

    print(f"\n  检查结果:")
    passed = 0
    failed = 0
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"    [{status}] {label}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n  通过 {passed} / {passed + failed}")
    return passed, failed


async def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, "templates", "data")
    user_dir = os.path.join(templates_dir, "user_generated")

    templates = [
        ("tech",  os.path.join(templates_dir, "tech.json")),
        ("toy",   os.path.join(templates_dir, "toy.json")),
        ("gen_1777900164", os.path.join(user_dir, "gen_1777900164.json")),
    ]

    print("=" * 60)
    print("统一模板测试")
    print("=" * 60)

    total_pass = 0
    total_fail = 0

    for template_id, path in templates:
        p, f = await test_template(template_id, path)
        total_pass += p
        total_fail += f

    print("\n" + "=" * 60)
    print(f"全部完成: 通过 {total_pass} / {total_pass + total_fail}")
    print("=" * 60)

    if total_fail > 0:
        sys.exit(1)
    else:
        print("[PASS] 全部模板测试通过！")


if __name__ == "__main__":
    asyncio.run(main())
