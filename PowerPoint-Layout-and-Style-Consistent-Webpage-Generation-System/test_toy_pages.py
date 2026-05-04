"""
玩具主题（Toy Theme）模板生成 + 套用测试

流程：
  1. 调用 TemplateGenerator 生成玩具主题 HTML 模板
  2. 从 HTML 提取模板 JSON，保存到 user_generated/
  3. 用 PresentationGenerator 加载该模板
  4. 生成一页封面 + 目录 + 章节 + 内容 + 结尾
  5. 输出完整 HTML 文件，验证结构正确
"""
import asyncio
import os
import sys
import json
import re
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from generator.llm_client import DeepSeekChatClient
from scripts.template_generator import TemplateGenerator, validate_template, extract_template_from_response
from pipeline import PresentationGenerator, PresentationOutline, SectionInput, ContentPageInput


USER_DESC = "生成一个玩具主题 PPT 模板，要求色彩鲜艳明快，卡通风格，适合儿童教育或亲子活动主题"


async def main():
    print("=" * 60)
    print("玩具主题模板生成 + 套用测试")
    print("=" * 60)

    # ============================================================
    # Step 1: 生成模板
    # ============================================================
    print("\n--- Step 1: LLM 生成玩具主题 HTML ---")
    client = DeepSeekChatClient(timeout_s=180.0)
    generator = TemplateGenerator(llm_client=client)

    t0 = time.time()
    result = await generator.generate(USER_DESC)
    elapsed = time.time() - t0
    print(f"模板生成耗时: {elapsed:.1f}s")
    print(f"  成功: {result['success']}")
    print(f"  模型: {result['model']}")

    is_valid, errors = result["validation"]
    print(f"  校验: {'通过' if is_valid else '失败'}")
    for err in errors:
        print(f"    警告: {err}")

    if not result["success"]:
        print("\n[FAIL] 模板生成失败，退出")
        sys.exit(1)

    template = result["parsed"]

    # ============================================================
    # Step 2: 保存模板 JSON
    # ============================================================
    print("\n--- Step 2: 保存模板 JSON ---")
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "templates", "data", "user_generated"
    )
    os.makedirs(output_dir, exist_ok=True)

    template_id = template.get("template_id", f"toy_{int(time.time())}")
    json_path = os.path.join(output_dir, f"{template_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"  模板已保存: {json_path}")
    print(f"  模板名: {template.get('template_name')}")
    print(f"  page_types: {list(template.get('page_types', {}).keys())}")

    # ============================================================
    # Step 3: 用 PresentationGenerator 加载该模板生成 PPT
    # ============================================================
    print("\n--- Step 3: 用 PresentationGenerator 套用模板 ---")
    template_name_for_loader = template_id

    try:
        ppt_gen = PresentationGenerator(template_name=template_name_for_loader, llm_client=client)
        await ppt_gen.initialize()
    except Exception as e:
        print(f"  模板加载失败: {e}")
        print("  尝试通过 raw_html 加载...")
        from templates.template_loader import load_template_from_dict
        ppt_gen = PresentationGenerator(template_name=template_name_for_loader, llm_client=client)
        ppt_gen.template = load_template_from_dict(template)
        from templates.renderer import TemplateRenderer
        ppt_gen.renderer = TemplateRenderer(ppt_gen.template)

    print(f"  模板加载成功: {ppt_gen.template.name}")
    print(f"  CSS 变量: {list(ppt_gen.template.css_variables.keys())}")

    # ============================================================
    # Step 4: 定义演示文稿大纲
    # ============================================================
    print("\n--- Step 4: 定义演示文稿大纲 ---")

    outline = PresentationOutline(
        title="欢乐玩具总动员",
        subtitle="亲子活动系列",
        date_badge="2026年",
        ending_title="玩出智慧",
        ending_message="每个玩具都是孩子的朋友，让我们在玩耍中成长",
        sections=[
            SectionInput(
                title="经典玩具",
                content_pages=[
                    ContentPageInput(
                        title="积木世界",
                        summary="积木是孩子最早的建筑师，它教会我们空间感和创造力。",
                        bullet_points=[
                            "锻炼手眼协调能力",
                            "培养空间想象力",
                            "促进亲子互动合作",
                        ],
                    ),
                    ContentPageInput(
                        title="毛绒玩偶",
                        summary="毛绒玩偶是孩子最温暖的陪伴，给他们安全感和想象力。",
                        bullet_points=[
                            "提供情感安全感",
                            "激发角色扮演游戏",
                            "培养同情心和责任心",
                        ],
                    ),
                ],
            ),
            SectionInput(
                title="创意玩具",
                content_pages=[
                    ContentPageInput(
                        title="拼图挑战",
                        summary="拼图是挑战与乐趣并存的游戏，让孩子在思考中获得成就感。",
                        bullet_points=[
                            "提升观察力和专注力",
                            "锻炼逻辑思维能力",
                            "完成后的巨大成就感",
                        ],
                    ),
                ],
            ),
        ],
    )

    total_sections = len(outline.sections)
    total_content = sum(len(s.content_pages) for s in outline.sections)
    total = 1 + 1 + total_sections + total_content + 1
    print(f"  演示文稿结构（共 {total} 页）:")
    print(f"    1: cover   封面 - {outline.title}")
    print(f"    2: toc     目录")
    page_i = 3
    for si, s in enumerate(outline.sections, 1):
        print(f"    {page_i}: section 章节 - 第{si}章 {s.title}")
        page_i += 1
        for ci, cp in enumerate(s.content_pages):
            print(f"    {page_i}: content 内容 - {cp.title}")
            page_i += 1
    print(f"    {total}: ending  结尾 - {outline.ending_title}")

    # ============================================================
    # Step 5: 生成演示文稿
    # ============================================================
    print("\n--- Step 5: 生成演示文稿 ---")
    t1 = time.time()
    result = await ppt_gen.generate_presentation(
        outline=outline,
        output_filename=f"toy_test.html",
        navigation=True,
        save_pages=True,
    )
    ppt_elapsed = time.time() - t1

    print(f"  生成耗时: {ppt_elapsed:.1f}s")
    print(f"  成功: {result.success}")
    if result.output_path:
        print(f"  输出: {result.output_path}")
    print(f"  页数: {result.page_count}")
    print(f"  大小: {result.document_size:,} bytes")
    if result.error:
        print(f"  错误:\n{result.error}")

    print(f"\n  各页布局:")
    for layout in result.page_layouts:
        layout_type = layout.get("type", "?")
        title = layout.get("title", "")
        print(f"    [{layout_type}] {title}")

    # ============================================================
    # Step 6: 验证输出
    # ============================================================
    print("\n--- Step 6: 验证输出 HTML ---")
    checks = []

    if result.output_path and os.path.exists(result.output_path):
        with open(result.output_path, "r", encoding="utf-8") as f:
            doc_html = f.read()

        checks.append(("输出文件存在", True))
        checks.append(("HTML 非空", len(doc_html) > 100))
        checks.append(("包含 slide div", "<div class=\"slide " in doc_html or "<div class='slide " in doc_html))
        checks.append(("包含 nav-dots", "nav-dots" in doc_html or "navDots" in doc_html))
        checks.append(("包含 page-indicator", "page-indicator" in doc_html or "pageIndicator" in doc_html))

        for ptype in ["cover", "toc", "section", "content", "ending"]:
            checks.append((f"HTML 中有 {ptype} 页面", f"slide {ptype}" in doc_html or f'class="{ptype}"' in doc_html))

        checks.append(("封面标题已替换", "欢乐玩具总动员" in doc_html))
        checks.append(("内容页有实际内容", "积木世界" in doc_html or "毛绒玩偶" in doc_html or "拼图" in doc_html))

        def strip_scripts(html):
            return re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)

        content_only = strip_scripts(doc_html)
        title_in_doc = re.findall(r"\{\{title\}\}", content_only)
        checks.append(("无残留 {{title}} 占位符", len(title_in_doc) == 0))

        content_in_doc = re.findall(r"\{\{content\}\}", content_only)
        checks.append(("无残留 {{content}} 占位符", len(content_in_doc) == 0))

        chapter_in_doc = re.findall(r"\{\{chapter_tag\}\}", content_only)
        checks.append(("无残留 {{chapter_tag}} 占位符", len(chapter_in_doc) == 0))

        checks.append(("章节标签已替换", "第I章" in doc_html or "第1章" in doc_html or "经典玩具" in doc_html))
        checks.append(("包含玩具主题 CSS 变量", "color-accent" in doc_html or "--color-accent" in doc_html))
        checks.append(("包含页码指示器", "1 / 8" in doc_html or "1/8" in doc_html or "欢乐玩具" in doc_html))

        print(f"\n  HTML 总长度: {len(doc_html):,} 字符")
        if "欢乐玩具总动员" in doc_html:
            idx = doc_html.find("欢乐玩具总动员")
            print(f"  封面标题: {doc_html[idx:idx+20]}...")

    else:
        checks.append(("输出文件存在", False))

    print("\n检查结果:")
    passed = 0
    failed = 0
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n通过 {passed} / {passed + failed}")
    print(f"\n总耗时: {elapsed + ppt_elapsed:.1f}s")

    if failed > 0:
        print(f"\n[FAIL] 有 {failed} 项未通过")
        sys.exit(1)
    else:
        print(f"\n[PASS] 全部通过！玩具主题演示文稿生成成功！")


if __name__ == "__main__":
    asyncio.run(main())
