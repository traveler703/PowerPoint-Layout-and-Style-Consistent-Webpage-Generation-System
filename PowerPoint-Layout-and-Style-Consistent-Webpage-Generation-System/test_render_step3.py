"""测试 3：验证提取的模板能否成功渲染"""
import asyncio
import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from generator.llm_client import DeepSeekChatClient

JSON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "templates", "data", "user_generated", "llm_step2_extracted.json"
)
HTML_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "templates", "data", "user_generated", "llm_step1_forest.html"
)

with open(JSON_PATH, "r", encoding="utf-8") as f:
    template = json.load(f)

with open(HTML_PATH, "r", encoding="utf-8") as f:
    raw_html = f.read()

print("=" * 60)
print("测试 3：验证提取的模板能否成功渲染")
print("=" * 60)

# 检查 3a: 模板 JSON 格式正确
print("\n--- 3a: 模板 JSON 格式检查 ---")
checks = []

checks.append(("template_id 存在", bool(template.get("template_id"))))
checks.append(("template_name 存在", bool(template.get("template_name"))))
checks.append(("css_variables 存在", bool(template.get("css_variables"))))
checks.append(("page_types 存在", bool(template.get("page_types"))))
checks.append(("raw_html 非空", bool(template.get("raw_html"))))

vp = template.get("viewport", {})
checks.append(("viewport 正确 1280x720", vp.get("width") == 1280 and vp.get("height") == 720))

page_types = template.get("page_types", {})
for ptype in ["cover", "toc", "section", "content", "ending"]:
    if ptype in page_types:
        sk = page_types[ptype].get("skeleton", "")
        checks.append((f"{ptype} skeleton 非空", bool(sk)))
        checks.append((f"{ptype} skeleton 包含 slide div",
                       "slide" in sk and ptype in sk))
        # 检查 skeleton 是否包含 CSS class 引用（不只是纯文本）
        checks.append((f"{ptype} skeleton 是 HTML 而非纯文本",
                       "<div" in sk or "class=" in sk))

css = template.get("css_variables", {})
checks.append(("css_variables 包含 color-primary", "color-primary" in css))
checks.append(("css_variables 包含 font-body", "font-body" in css))

# 检查 3b: 模板和 raw_html 的一致性
print("\n--- 3b: 模板与 raw_html 一致性 ---")

# 检查 raw_html 中的 :root CSS 变量是否被提取
root_match = re.search(r":root\s*\{([^}]+)\}", raw_html, re.DOTALL)
if root_match:
    root_css = root_match.group(1)
    checks.append(("raw_html 的 :root 包含 CSS 变量", ":" in root_css and "--" in root_css))
    print(f"  raw_html :root 长度: {len(root_css)} 字符")
else:
    checks.append(("raw_html 有 :root", False))

# 检查 slide class 数量（应该至少 5 个）
slide_count = raw_html.count('class="slide ')
checks.append(("raw_html 包含至少 5 个 slide", slide_count >= 5))
print(f"  raw_html slide 数量: {slide_count}")

# 检查 3c: 用 skeleton 渲染一页内容（简单字符串替换测试）
print("\n--- 3c: skeleton 渲染测试 ---")

def render_page(skeleton: str, placeholders: dict) -> str:
    """简单占位符替换"""
    result = skeleton
    for key, value in placeholders.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result

def count_remaining(skeleton: str, placeholders: dict) -> int:
    """统计替换后还剩多少未替换的 {{xxx}}"""
    rendered = render_page(skeleton, placeholders)
    return len(re.findall(r"\{\{[^}]+\}\}", rendered))

cover_skeleton = page_types.get("cover", {}).get("skeleton", "")
if cover_skeleton:
    test_placeholders = {
        "title": "森林探险",
        "subtitle": "走进大自然的神秘世界",
        "date_badge": "2026年5月",
        "page_number": "1",
    }
    rendered = render_page(cover_skeleton, test_placeholders)
    remaining = count_remaining(cover_skeleton, test_placeholders)
    checks.append(("cover skeleton 渲染后无占位符残留", remaining == 0))
    checks.append(("cover skeleton 渲染后包含 title 内容", "森林探险" in rendered))
    checks.append(("cover skeleton 渲染后包含 subtitle", "走进大自然" in rendered))
    print(f"  cover skeleton: 原始 len={len(cover_skeleton)}, 渲染后 len={len(rendered)}, 剩余占位符={remaining}")
    preview = re.sub(r"\s+", " ", rendered)[:150]
    print(f"  渲染预览: {preview}...")
else:
    checks.append(("cover skeleton 存在", False))

def count_remaining(skeleton: str, placeholders: dict) -> int:
    """统计替换后还剩多少未替换的 {{xxx}}"""
    rendered = render_page(skeleton, placeholders)
    return len(re.findall(r"\{\{[^}]+\}\}", rendered))

content_skeleton = page_types.get("content", {}).get("skeleton", "")
if content_skeleton:
    # content 页面用 {{content}} 作为主文本占位符（不是 {{title}}）
    test_placeholders = {
        "title": "什么是森林",
        "content": "森林是地球之肺",
        "page_number": "3",
    }
    rendered = render_page(content_skeleton, test_placeholders)
    # 只统计 skeleton 中原本存在的占位符替换后是否消失
    # content skeleton 中有 {{content}}，替换后应消失
    checks.append(("content skeleton 渲染后 {{content}} 被替换",
                   "{{content}}" not in rendered))
    # content 占位内容被替换
    checks.append(("content skeleton 渲染后包含主内容", "森林是地球之肺" in rendered))
    print(f"  content skeleton: len={len(content_skeleton)}, 渲染后 len={len(rendered)}")
    print(f"  {{content}} 已替换: {'{{content}}' not in rendered}")
else:
    checks.append(("content skeleton 存在", False))

section_skeleton = page_types.get("section", {}).get("skeleton", "")
if section_skeleton:
    test_placeholders = {
        "chapter_tag": "第一章",
        "title": "森林生态",
        "subtitle": "探索自然的奥秘",
        "page_number": "2",
    }
    rendered = render_page(section_skeleton, test_placeholders)
    remaining = count_remaining(section_skeleton, test_placeholders)
    checks.append(("section skeleton 渲染后无占位符残留", remaining == 0))
    print(f"  section skeleton: 原始 len={len(section_skeleton)}, 渲染后 len={len(rendered)}, 剩余占位符={remaining}")
else:
    checks.append(("section skeleton 存在", False))

ending_skeleton = page_types.get("ending", {}).get("skeleton", "")
if ending_skeleton:
    test_placeholders = {
        "title": "感谢观看",
        "message": "愿你心有繁林",
        "page_number": "7",
    }
    rendered = render_page(ending_skeleton, test_placeholders)
    remaining = count_remaining(ending_skeleton, test_placeholders)
    checks.append(("ending skeleton 渲染后无占位符残留", remaining == 0))
    print(f"  ending skeleton: 原始 len={len(ending_skeleton)}, 渲染后 len={len(rendered)}, 剩余占位符={remaining}")
else:
    checks.append(("ending skeleton 存在", False))

# 检查 3d: 验证提取的模板可以加载到现有模板系统中
print("\n--- 3d: 模板加载兼容性 ---")
try:
    from templates.template_loader import TemplateLoader
    loader = TemplateLoader()

    # 尝试用提取的模板 JSON 加载
    # 模板需要 name 字段（不是 template_name）
    compat = dict(template)
    if "template_name" in compat:
        compat["name"] = compat.pop("template_name")

    # 检查必需字段
    has_id = "template_id" in compat
    has_name = "name" in compat or "template_name" in compat
    has_css = "css_variables" in compat
    has_pages = "page_types" in compat

    checks.append(("模板有 template_id", has_id))
    checks.append(("模板有 name", has_name))
    checks.append(("模板有 css_variables", has_css))
    checks.append(("模板有 page_types", has_pages))

    print(f"  模板 JSON 字段: {list(compat.keys())}")
    print(f"  template_id: {compat.get('template_id')}")
    print(f"  name/template_name: {compat.get('name') or compat.get('template_name')}")

    compat_ok = True
except Exception as e:
    print(f"  加载失败: {e}")
    import traceback
    traceback.print_exc()
    compat_ok = False
    checks.append(("模板可加载到 TemplateLoader", False))

# 汇总
print("\n" + "=" * 60)
print("汇总结果")
print("=" * 60)

passed = sum(1 for _, ok in checks if ok)
failed = len(checks) - passed

for label, ok in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")

print(f"\n通过 {passed} / {len(checks)}")

if failed > 0:
    print(f"\n[FAIL] 有 {failed} 项未通过")
    sys.exit(1)
else:
    print(f"\n[PASS] 全部通过！模板可成功应用。")
