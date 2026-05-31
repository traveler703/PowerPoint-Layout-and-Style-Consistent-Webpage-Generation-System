"""
模板生成功能测试

测试 LLM 驱动的模板生成全流程：
1. 通过 /api/llm/chat (mode=template) 生成模板
2. 验证模板结构完整性
3. 通过 /api/templates POST 保存模板
4. 通过 /api/templates GET 确认模板已注册
"""
import json, os, sys, time, requests

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "http://127.0.0.1:5000"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "template_gen")

# 固定的模板风格描述（不依赖 LLM 动态生成内容）
TEMPLATE_DESCRIPTION = """
设计一个"深海极光"主题的PPT模板。
- 配色：深海蓝、极光绿、冰白色，深色背景为主
- 风格：科技感、未来感、适合科技产品发布和行业报告
- 字体：适合中文展示的现代无衬线字体（如思源黑体）
- 装饰：极光光晕、几何线条、微光粒子效果
- 整体感觉：专业、前卫、富有科技美学
"""


def log(msg=""):
    print(msg, flush=True)


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_backend():
    """检查后端是否运行"""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def step1_generate_template():
    """调用 LLM 生成模板"""
    log("=" * 60)
    log("Step 1: 调用 LLM 生成模板")
    log(f"  描述: {TEMPLATE_DESCRIPTION.strip()[:80]}...")
    log()

    t0 = time.time()
    resp = requests.post(f"{BASE_URL}/api/llm/chat", json={
        "messages": [{"role": "user", "content": TEMPLATE_DESCRIPTION.strip()}],
        "mode": "template",
    }, timeout=600)

    elapsed = time.time() - t0
    log(f"  耗时: {elapsed:.0f}s")

    if resp.status_code != 200:
        log(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:500]}")
        return None

    data = resp.json()
    if not data.get("success"):
        log(f"  [FAIL] success=False")
        validation = data.get("validation", {})
        log(f"  validation errors: {validation.get('errors', [])}")
        return None

    parsed = data.get("parsed", {})
    validation = data.get("validation", {})

    log(f"  template_id: {parsed.get('template_id')}")
    log(f"  template_name: {parsed.get('template_name')}")
    log(f"  validation valid: {validation.get('valid')}")
    log(f"  validation errors: {len(validation.get('errors', []))}")

    css = parsed.get("css_variables", {})
    log(f"  CSS variables ({len(css)}):")
    for k, v in css.items():
        log(f"    {k}: {v}")

    page_types = parsed.get("page_types", {})
    log(f"  page_types ({len(page_types)}): {list(page_types.keys())}")
    for pt, cfg in page_types.items():
        sk = cfg.get("skeleton", "")
        has_title = "{{title}}" in sk
        has_page_num = "{{page_number}}" in sk or "page-num" in sk
        has_footer = "slide-footer" in sk
        log(f"    {pt}: skeleton={len(sk)}chars, title={'✓' if has_title else '✗'}, "
            f"pagenum={'✓' if has_page_num else '✗'}, footer={'✓' if has_footer else '✗'}")

    # 保存原始响应
    path = os.path.join(OUTPUT_DIR, "01_llm_response.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"\n  已保存原始响应: {path}")

    return parsed


def step2_validate_template(parsed):
    """本地验证模板结构"""
    log()
    log("=" * 60)
    log("Step 2: 本地验证模板结构")

    errors = []

    # 必需的顶层字段
    required_fields = ["template_id", "template_name", "css_variables", "page_types", "viewport", "raw_html"]
    for f in required_fields:
        if f not in parsed:
            errors.append(f"缺少顶层字段: {f}")

    # viewport
    vp = parsed.get("viewport", {})
    if vp.get("width") != 1280 or vp.get("height") != 720:
        errors.append(f"viewport 尺寸不正确: {vp}")

    # page_types
    required_types = {"cover", "toc", "section", "content", "ending"}
    pt = parsed.get("page_types", {})
    missing = required_types - set(pt.keys())
    if missing:
        errors.append(f"缺少 page_type: {missing}")

    for ptype in required_types:
        if ptype not in pt:
            continue
        cfg = pt[ptype]
        sk = cfg.get("skeleton", "")
        if len(sk.strip()) < 20:
            errors.append(f"page_types.{ptype} skeleton 太短 ({len(sk)} chars)")
        if "slide-footer" not in sk:
            errors.append(f"page_types.{ptype} 缺少 slide-footer")
        if ptype in ("content", "toc", "section") and "{{title}}" not in sk:
            errors.append(f"page_types.{ptype} 缺少 {{{{title}}}} 占位符")

    # CSS variables
    css = parsed.get("css_variables", {})
    required_css = ["color-primary", "color-background", "color-text"]
    for k in required_css:
        if not css.get(k):
            errors.append(f"css_variables 缺少或为空: {k}")

    if errors:
        log(f"  [FAIL] {len(errors)} 个验证错误:")
        for e in errors:
            log(f"    - {e}")
        return False
    else:
        log(f"  [PASS] 模板结构验证通过")
        return True


def step3_save_template(parsed):
    """保存模板到服务端"""
    log()
    log("=" * 60)
    log("Step 3: 保存模板到服务端 (POST /api/templates)")

    template_data = {
        "template_id": parsed["template_id"],
        "template_name": parsed.get("template_name", "新模板"),
        "description": parsed.get("description", ""),
        "version": "1.0.0",
        "css_variables": parsed.get("css_variables", {}),
        "page_types": parsed.get("page_types", {}),
        "viewport": parsed.get("viewport", {"width": 1280, "height": 720}),
        "tags": parsed.get("tags", ["自定义"]),
        "template_type": "user",
        "raw_html": parsed.get("raw_html", ""),
    }

    resp = requests.post(f"{BASE_URL}/api/templates", json={
        "template_data": template_data,
    }, timeout=30)

    if resp.status_code not in (200, 201):
        log(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:500]}")
        return None

    data = resp.json()
    if not data.get("success"):
        log(f"  [FAIL] {data.get('error', 'unknown')}")
        return None

    tpl = data.get("template", {})
    log(f"  [PASS] 模板已保存")
    log(f"  template_id: {tpl.get('template_id')}")
    log(f"  template_name: {tpl.get('template_name')}")
    log(f"  page_types: {tpl.get('page_types', [])}")

    # 保存响应
    path = os.path.join(OUTPUT_DIR, "02_saved_template.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"  已保存: {path}")

    return parsed["template_id"]


def step4_verify_template_list(template_id):
    """通过 GET /api/templates 确认模板已注册"""
    log()
    log("=" * 60)
    log("Step 4: 验证模板列表 (GET /api/templates)")

    resp = requests.get(f"{BASE_URL}/api/templates", timeout=10)
    if resp.status_code != 200:
        log(f"  [FAIL] HTTP {resp.status_code}")
        return False

    data = resp.json()
    templates = data.get("templates", [])
    found = any(t.get("template_id") == template_id for t in templates)

    if found:
        log(f"  [PASS] 模板 {template_id} 已在列表中 (共 {len(templates)} 个模板)")
    else:
        log(f"  [FAIL] 模板 {template_id} 不在列表中")

    # 列出所有模板
    log(f"\n  当前所有模板:")
    for t in templates:
        tag = " [NEW]" if t.get("template_id") == template_id else ""
        log(f"    - {t.get('template_id'):20s} | {t.get('template_name', '')[:30]}{tag}")

    return found


def main():
    log("=" * 60)
    log("模板生成功能测试")
    log(f"输出目录: {OUTPUT_DIR}")
    log()

    if not check_backend():
        log("[FAIL] 后端未启动，请先运行: python app.py")
        sys.exit(1)
    log("[INFO] 后端运行正常")
    log()

    ensure_output_dir()

    # Step 1: 生成模板
    parsed = step1_generate_template()
    if not parsed:
        log("\n[ABORT] 模板生成失败")
        sys.exit(1)

    # Step 2: 本地验证
    step2_validate_template(parsed)

    # Step 3: 保存到服务端
    template_id = step3_save_template(parsed)
    if not template_id:
        log("\n[ABORT] 模板保存失败")
        sys.exit(1)

    # Step 4: 验证注册
    step4_verify_template_list(template_id)

    log()
    log("=" * 60)
    log("模板生成测试完成")
    log(f"  模板ID: {template_id}")
    log(f"  输出目录: {OUTPUT_DIR}")
    log()


if __name__ == "__main__":
    main()
