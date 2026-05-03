"""快速测试：从 forest_raw.html 提取模板信息"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from scripts.template_generator import extract_template_from_response

with open("templates/data/user_generated/forest_raw.html", "r", encoding="utf-8") as f:
    html_content = f.read()

print(f"HTML 长度: {len(html_content)}")

try:
    result = extract_template_from_response(html_content, "森林主题PPT模板")
    print("提取成功!")
    print(f"template_id: {result.get('template_id')}")
    print(f"CSS 变量数: {len(result.get('css_variables', {}))}")
    print(f"page_types: {list(result.get('page_types', {}).keys())}")
    print()
    for ptype, config in result.get("page_types", {}).items():
        sk = config.get("skeleton", "")
        placeholders = config.get("placeholders", [])
        print(f"  {ptype}: skeleton 长度={len(sk)}, 占位符={placeholders}")
        if sk:
            preview = re.sub(r"\s+", " ", sk)[:120]
            print(f"    预览: {preview}...")
except Exception as e:
    print(f"提取失败: {e}")
    import traceback
    traceback.print_exc()
