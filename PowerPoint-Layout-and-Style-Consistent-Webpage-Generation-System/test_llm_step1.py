"""测试 1：LLM 生成 HTML 是否正确"""
import asyncio
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from generator.llm_client import DeepSeekChatClient
from scripts.template_generator import TemplateGenerator

USER_DESC = "生成一个森林主题 PPT 模板，要求每个页面都有绿叶装饰元素，页脚是森林主题的古诗词，背景使用绿色系配色"


async def main():
    client = DeepSeekChatClient(timeout_s=180.0)
    generator = TemplateGenerator(llm_client=client)

    print("=" * 60)
    print("测试 1：LLM 生成 HTML（带自动重试）")
    print("=" * 60)
    print(f"用户需求: {USER_DESC[:50]}...")

    result = await generator.generate(USER_DESC)

    print(f"\n模型: {result['model']}")
    print(f"成功: {result['success']}")

    is_valid, errors = result["validation"]
    print(f"校验: {'通过' if is_valid else '失败'}")
    for err in errors:
        print(f"  警告: {err}")

    if not result["success"]:
        print(f"\n[FAIL] 生成失败")
        sys.exit(1)

    response = result["response"]["html"]
    print(f"\n响应总长度: {len(response)} 字符")

    cleaned = response.strip()
    cleaned = re.sub(r"^```html\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    print(f"清理后长度: {len(cleaned)} 字符")

    checks = []

    ok = "<!DOCTYPE html>" in cleaned or "<html" in cleaned
    checks.append(("HTML 有效", ok))

    ok = ":root" in cleaned
    checks.append(("包含 :root CSS 变量", ok))

    for ptype in ["cover", "toc", "section", "content", "ending"]:
        ok = (
            f'class="slide {ptype}"' in cleaned
            or f"class='slide {ptype}'" in cleaned
            or f"slide {ptype}" in cleaned
        )
        checks.append((f"包含 slide {ptype}", ok))

    checks.append(("包含 {{SLIDES_CONTENT}}", "{{SLIDES_CONTENT}}" in cleaned))
    checks.append(("包含 {{TOTAL_PAGES}}", "{{TOTAL_PAGES}}" in cleaned))
    checks.append(("包含 slide-footer", "slide-footer" in cleaned))
    checks.append(("包含 page-num", "page-num" in cleaned))
    checks.append(("包含 --color- CSS 变量", "--color-" in cleaned))

    # content 页 {{title}} 在 {{content}} 之前
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(cleaned, "html.parser")
    content_div = soup.find("div", class_=lambda c: c and "content" in c.split())
    if content_div:
        sk = str(content_div)
        title_pos = sk.find("{{title}}")
        content_pos = sk.find("{{content}}")
        if title_pos != -1 and content_pos != -1:
            ok = title_pos < content_pos
        elif title_pos != -1:
            ok = True
        else:
            ok = False
        checks.append(("content 页 {{title}} 在 {{content}} 之前", ok))

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
    print(f"\n--- HTML（前 1500 字符）---")
    print(cleaned[:1500])

    if failed > 0:
        print(f"\n[FAIL] {failed} 项未通过")
        sys.exit(1)
    else:
        print(f"\n[PASS] 全部通过！")
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "templates", "data", "user_generated", "llm_step1_forest.html"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        print(f"已保存: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
