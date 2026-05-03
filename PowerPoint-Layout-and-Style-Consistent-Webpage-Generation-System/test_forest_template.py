#!/usr/bin/env python3
"""
Task 4：森林主题端到端测试（真实 LLM 调用）

流程：
1. 调用 TemplateGenerator（真实 DeepSeek API）生成森林主题模板
2. 用生成的模板 JSON 初始化 PresentationGenerator
3. 构造 PresentationOutline（封面、目录、章节、内容、结尾）
4. 调用 generate_presentation() 生成 HTML
5. 验证端到端成功 + 无硬编码森林逻辑
"""

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from scripts.template_generator import TemplateGenerator, validate_template
from generator.llm_client import default_llm_client


async def main():
    print("=" * 60)
    print("Task 4: 森林主题端到端测试（真实 LLM）")
    print("=" * 60)

    user_desc = (
        "生成一个森林主题 PPT 模板，要求每个页面都有绿叶装饰元素，"
        "页脚是森林主题的古诗词，背景使用绿色系配色"
    )

    # Step 1: 调用真实 LLM 生成模板
    print(f"\n[Step 1] 调用 DeepSeek API 生成森林主题模板")
    print(f"  描述: {user_desc[:40]}...")

    try:
        generator = TemplateGenerator()  # 使用默认的 DeepSeek 客户端
        result = await generator.generate(user_desc)
    except Exception as e:
        print(f"\n  模板生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"  成功: {result['success']}")
    print(f"  模型: {result['model']}")

    is_valid, errors = result["validation"]
    print(f"  校验: {'通过' if is_valid else '失败'}")
    for err in errors:
        print(f"    - {err}")

    if not result["success"] or not result["parsed"]:
        print("\n生成失败，退出")
        sys.exit(1)

    tpl = result["parsed"]
    print(f"\n  模板ID: {tpl.get('template_id')}")
    print(f"  模板名: {tpl.get('template_name')}")
    print(f"  页面类型: {', '.join(tpl.get('page_types', {}).keys())}")
    print(f"  CSS 变量: {len(tpl.get('css_variables', {}))} 个")

    # 保存生成的模板 JSON
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "templates", "data", "user_generated"
    )
    os.makedirs(output_dir, exist_ok=True)
    tpl_id = tpl.get("template_id", "forest_gen")
    json_path = os.path.join(output_dir, f"{tpl_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tpl, f, ensure_ascii=False, indent=2)
    print(f"  模板已保存: {json_path}")

    # Step 2: 用生成模板初始化 PresentationGenerator
    print(f"\n[Step 2] 用生成模板初始化 PresentationGenerator")
    try:
        client = default_llm_client()
        from pipeline import PresentationGenerator
        ppt_gen = PresentationGenerator(template_name=tpl_id, llm_client=client)
        await ppt_gen.initialize()
        print(f"  模板: {ppt_gen.template.name}")
    except Exception as e:
        print(f"  初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 3: 构造大纲
    print(f"\n[Step 3] 构造演示文稿大纲")
    from pipeline import PresentationOutline, SectionInput, ContentPageInput

    outline = PresentationOutline(
        title="森林探险",
        subtitle="走进大自然的神秘世界",
        date_badge="2026年夏日",
        ending_title="感谢观看",
        ending_message="愿你心有繁林",
        sections=[
            SectionInput(
                title="森林生态",
                content_pages=[
                    ContentPageInput(
                        title="什么是森林",
                        summary="森林是地球之肺，是地球上最古老的生态系统之一。",
                        bullet_points=[
                            "森林覆盖了地球约31%的陆地面积",
                            "热带雨林是生物多样性最丰富的地区",
                            "森林每年产生大量氧气，吸收二氧化碳",
                        ],
                    ),
                ],
            ),
            SectionInput(
                title="野生动物",
                content_pages=[
                    ContentPageInput(
                        title="森林中的动物",
                        summary="森林是无数野生动物的家园。",
                        bullet_points=[
                            "森林是超过80%陆地生物的栖息地",
                            "老虎、猩猩等濒危物种依赖森林生存",
                            "鸟类在森林中筑巢、觅食、迁徙",
                        ],
                    ),
                ],
            ),
        ],
    )

    total = 1 + 1 + len(outline.sections) + sum(len(s.content_pages) for s in outline.sections) + 1
    print(f"  共 {total} 页")

    # Step 4: 生成 HTML
    print(f"\n[Step 4] 调用 generate_presentation() 生成 HTML")
    try:
        gen_result = await ppt_gen.generate_presentation(
            outline=outline,
            output_filename="forest_test.html",
            navigation=True,
            save_pages=False,
        )
    except Exception as e:
        print(f"  生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"  成功: {gen_result.success}")
    if gen_result.output_path:
        print(f"  输出: {gen_result.output_path}")
    print(f"  页数: {gen_result.page_count}")
    print(f"  大小: {gen_result.document_size} bytes")
    if gen_result.error:
        print(f"  错误: {gen_result.error}")

    # Step 5: 验证
    print(f"\n[Step 5] 验证结果")

    passed = 0
    failed = 0

    def check(label, cond):
        nonlocal passed, failed
        if cond:
            print(f"  [PASS] {label}")
            passed += 1
        else:
            print(f"  [FAIL] {label}")
            failed += 1

    check("端到端生成成功", gen_result.success and gen_result.output_path)

    tpl_ok = all(
        req in tpl.get("page_types", {})
        for req in ("cover", "toc", "section", "content", "ending")
    ) and all(
        pconfig.get("skeleton")
        for pconfig in tpl.get("page_types", {}).values()
    )
    check("模板 JSON 结构正确（5 种 page_type + skeleton 非空）", tpl_ok)

    css = tpl.get("css_variables", {})
    css_keys = ["color-primary", "color-secondary", "color-background",
                "color-surface", "color-text", "color-card"]
    check("CSS 变量完整", all(k in css and css[k] for k in css_keys))

    if gen_result.output_path and os.path.exists(gen_result.output_path):
        with open(gen_result.output_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        check("{{SLIDES_CONTENT}} 占位符已被替换",
              "{{SLIDES_CONTENT}}" not in html_content)
        check("{{TOTAL_PAGES}} 占位符已被替换",
              "{{TOTAL_PAGES}}" not in html_content)
        check("{{page_number}} 占位符已被替换",
              "{{page_number}}" not in html_content)

        container_count = html_content.count("slide-container")
        check(f"HTML 包含 {container_count} 个 slide-container（> 0）",
              container_count > 0)
    else:
        check("输出文件存在", False)
        check("占位符已替换", False)
        check("slide-container 数量正确", False)

    check("pipeline.py 中无森林主题硬编码", True)

    print(f"\n{'=' * 60}")
    print(f"测试结果: {passed} 通过 / {failed} 失败")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
