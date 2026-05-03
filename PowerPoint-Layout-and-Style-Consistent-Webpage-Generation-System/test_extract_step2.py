"""测试 2：从 LLM 生成的 HTML 中提取模板信息"""
import sys
import os
import re
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from scripts.template_generator import (
    extract_template_from_response,
    validate_template,
    _extract_css_variables,
    _extract_page_types,
)

HTML_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "templates", "data", "user_generated", "llm_step1_forest.html"
)

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html_content = f.read()

print("=" * 60)
print("测试 2：从 HTML 提取模板信息")
print("=" * 60)
print(f"\nHTML 长度: {len(html_content)} 字符")

# 2a: CSS 变量提取
print("\n--- 2a: CSS 变量提取 ---")
css_vars = _extract_css_variables(html_content)
print(f"提取到 {len(css_vars)} 个 CSS 变量:")
for k, v in css_vars.items():
    print(f"  {k}: {v}")

css_checks = [
    ("至少 4 个 CSS 变量", len(css_vars) >= 4),
    ("有颜色变量", any(k.startswith("color") for k in css_vars)),
    ("有字体变量", any(k.startswith("font") for k in css_vars)),
]

# 2b: page_type skeleton 提取
print("\n--- 2b: page_type skeleton 提取 ---")
page_types = _extract_page_types(html_content)
print(f"提取到 {len(page_types)} 种 page_type:")
for ptype, config in page_types.items():
    sk = config.get("skeleton", "")
    print(f"  {ptype}: skeleton 长度={len(sk)}, 占位符={config.get('placeholders', [])}")
    if sk:
        preview = re.sub(r"\s+", " ", sk)[:120]
        print(f"    预览: {preview}...")

pt_checks = [
    ("至少提取到 3 种 page_type", len(page_types) >= 3),
    ("所有 skeleton 非空", all(config.get("skeleton") for config in page_types.values())),
]
for ptype in ["cover", "toc", "section", "content", "ending"]:
    ok = ptype in page_types
    pt_checks.append((f"提取到 {ptype}", ok))

# 2c: 完整提取
print("\n--- 2c: 完整提取 ---")
try:
    template = extract_template_from_response(html_content, "森林主题 PPT 模板")
    print(f"提取成功!")
    print(f"  template_id: {template.get('template_id')}")
    print(f"  template_name: {template.get('template_name')}")
    print(f"  CSS 变量: {len(template.get('css_variables', {}))} 个")
    print(f"  page_types: {list(template.get('page_types', {}).keys())}")
    print(f"  raw_html 长度: {len(template.get('raw_html', ''))} 字符")

    full_checks = [
        ("template_id 存在", bool(template.get("template_id"))),
        ("raw_html 非空", bool(template.get("raw_html"))),
        ("至少 3 种 page_type", len(template.get("page_types", {})) >= 3),
    ]
    extract_ok = True
except Exception as e:
    print(f"提取失败: {e}")
    import traceback
    traceback.print_exc()
    extract_ok = False
    full_checks = [("提取不抛异常", False)]

# 2d: 校验
print("\n--- 2d: 校验 ---")
if extract_ok:
    is_valid, errors = validate_template(template)
    print(f"校验结果: {'通过' if is_valid else '失败'}")
    for err in errors:
        print(f"  错误: {err}")

    val_checks = [
        ("CSS 变量存在", bool(template.get("css_variables"))),
        ("page_types 存在", bool(template.get("page_types"))),
        ("viewport 正确", template.get("viewport") == {"width": 1280, "height": 720}),
        ("5 种 page_type 齐全", set(template.get("page_types", {}).keys()) == {"cover", "toc", "section", "content", "ending"}),
    ]
else:
    val_checks = [("校验通过", False)]

# 汇总
print("\n" + "=" * 60)
print("汇总结果")
print("=" * 60)

all_checks = css_checks + pt_checks + full_checks + val_checks
passed = sum(1 for _, ok in all_checks if ok)
failed = len(all_checks) - passed

for label, ok in all_checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")

print(f"\n通过 {passed} / {len(all_checks)}")

if failed > 0:
    print(f"\n[FAIL] 有 {failed} 项未通过")
    sys.exit(1)
else:
    print(f"\n[PASS] 全部通过！")
    # 保存提取结果
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "templates", "data", "user_generated", "llm_step2_extracted.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"已保存提取结果到: {out_path}")
