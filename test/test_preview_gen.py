"""
端到端测试：模板生成 → PPT预览生成

使用固定的9页大纲内容（不依赖LLM动态生成内容）：
  cover ×1, toc ×1, section ×2, content ×4, ending ×1

测试流程:
  1. 调用 /api/llm/chat (mode=template) 生成模板
  2. 本地验证模板结构
  3. 保存模板到 /api/templates
  4. 用固定大纲调用 /api/generate-ppt-progress 生成PPT
  5. 验证PPT结构正确性
"""
import json, os, sys, time, re, requests

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "http://127.0.0.1:5000"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "preview_gen")

# ============================================================
# 固定大纲内容 — 不依赖 LLM 动态生成
# ============================================================
FIXED_OUTLINE = [
    {"page_type": "cover",   "title": "产品战略发布会", "subtitle": "创新驱动增长", "date_badge": "2026年6月"},
    {"page_type": "toc",     "title": "目录", "bullets": [
        "第一章 市场趋势与机遇",
        "第二章 核心产品矩阵",
        "第三章 技术架构升级",
        "第四章 战略规划与展望",
    ]},
    {"page_type": "section", "title": "第一章", "subtitle": "市场趋势与机遇"},
    {"page_type": "content", "title": "行业现状分析", "bullets": [
        "全球数字化转型加速，AI 技术深入各行各业",
        "2026年全球企业级SaaS市场规模预计突破3000亿美元",
        "AI Agent 技术成为企业效率提升的关键驱动力",
        "数据安全与隐私合规需求持续增长",
    ]},
    {"page_type": "content", "title": "我们的竞争优势", "bullets": [
        "自研大模型在垂直领域准确率领先行业15%",
        "服务超过500家企业客户，覆盖金融、制造、医疗",
        "获得ISO27001/SOC2国际安全认证",
        "核心团队来自顶级互联网公司与研究机构",
    ]},
    {"page_type": "section", "title": "第二章", "subtitle": "核心产品矩阵"},
    {"page_type": "content", "title": "产品体系概览", "bullets": [
        "SmartChat：新一代企业级AI对话平台",
        "DataPilot：智能数据分析与可视化工具",
        "FlowMaster：低代码业务流程自动化引擎",
        "三款产品深度集成，形成完整解决方案",
    ]},
    {"page_type": "content", "title": "技术路线图", "bullets": [
        "Q1：完成大模型v3.0训练，上下文窗口扩展至1M",
        "Q2：推出分布式推理引擎，推理成本降低60%",
        "Q3：上线多模态理解能力，覆盖图像、音频、视频",
        "Q4：开放API平台，支持第三方开发者生态",
    ]},
    {"page_type": "ending",  "title": "谢谢观看", "subtitle": "期待与您携手共创未来"},
]


def log(msg=""):
    print(msg, flush=True)


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_backend():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def save_json(filename, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"  [SAVE] {path}")
    return path


def save_html(filename, html):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    kb = len(html.encode("utf-8")) / 1024
    log(f"  [SAVE] {path} ({kb:.1f} KB)")
    return path


# ============================================================
# Step 1: 生成模板
# ============================================================
def step1_generate_template():
    log("=" * 60)
    log("Step 1: LLM 生成模板")
    log()

    description = (
        "设计一个自然森林风格的PPT模板。"
        "配色：翡翠绿、木质棕、奶油白，浅色背景为主。"
        "风格：清新自然、温暖舒适，适合环保、教育、生活方式类演示。"
        "字体：优雅的衬线字体搭配清新的无衬线字体。"
        "装饰：树叶轮廓、柔和的自然光影、有机曲线。"
    )
    log(f"  描述: {description[:80]}...")

    t0 = time.time()
    resp = requests.post(f"{BASE_URL}/api/llm/chat", json={
        "messages": [{"role": "user", "content": description}],
        "mode": "template",
    }, timeout=600)
    elapsed = time.time() - t0

    log(f"  耗时: {elapsed:.0f}s")
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:300]}"

    data = resp.json()
    assert data.get("success"), f"success=False, errors: {data.get('validation', {}).get('errors', [])}"

    parsed = data["parsed"]
    validation = data.get("validation", {})

    log(f"  template_id: {parsed['template_id']}")
    log(f"  template_name: {parsed.get('template_name', '')}")
    log(f"  validation: {validation.get('valid')}, errors={len(validation.get('errors', []))}")

    css = parsed.get("css_variables", {})
    log(f"  CSS vars: {len(css)}")
    for k in ["color-primary", "color-background", "color-text"]:
        log(f"    {k}: {css.get(k, 'MISSING')}")

    page_types = parsed.get("page_types", {})
    log(f"  page_types: {sorted(page_types.keys())}")
    assert set(page_types.keys()) >= {"cover", "toc", "section", "content", "ending"}, \
        f"缺少 page_type: {set(page_types.keys())}"

    # 检查每个 skeleton 的关键占位符
    checks = {
        "cover": ["{{title}}"],
        "toc": ["{{title}}", "{{toc_items}}"],
        "section": ["{{title}}", "{{chapter_tag}}"],
        "content": ["{{title}}", "{{content}}"],
        "ending": ["{{title}}", "{{message}}"],
    }
    for pt, required_phs in checks.items():
        sk = page_types.get(pt, {}).get("skeleton", "")
        for ph in required_phs:
            assert ph in sk, f"{pt} 页缺少占位符 {ph}"

    # 检查关键约束
    content_sk = page_types["content"]["skeleton"]
    title_pos = content_sk.find("{{title}}")
    content_pos = content_sk.find("{{content}}")
    assert title_pos < content_pos, f"content 页 {{{{title}}}} 在 {{{{content}}}} 之后!"
    # .page-content 内不应有装饰div/svg
    pc_match = re.search(
        r'<div[^>]*class="[^"]*\bpage-content\b[^"]*"[^>]*>(.*?)</div>',
        content_sk, re.DOTALL | re.IGNORECASE,
    )
    if pc_match:
        inner_clean = pc_match.group(1).replace("{{content}}", "").strip()
        assert not re.search(r'<(?:div|svg|span)', inner_clean), \
            f"content 页 .page-content 内有装饰元素: {inner_clean[:100]}"

    log("  [PASS] 模板结构验证通过")
    save_json("01_llm_response.json", data)
    return parsed


# ============================================================
# Step 2: 保存模板
# ============================================================
def step2_save_template(parsed):
    log()
    log("=" * 60)
    log("Step 2: 保存模板 (POST /api/templates)")
    log()

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

    assert resp.status_code in (200, 201), f"HTTP {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert data.get("success"), f"保存失败: {data.get('error', 'unknown')}"

    tpl = data.get("template", {})
    log(f"  [PASS] 模板已保存: {tpl.get('template_id')}")
    log(f"  page_types: {tpl.get('page_types', [])}")

    save_json("02_saved_template.json", data)
    return parsed["template_id"]


# ============================================================
# Step 3: 生成预览 PPT
# ============================================================
def step3_generate_preview(template_id):
    log()
    log("=" * 60)
    log(f"Step 3: 生成预览 PPT (模板: {template_id})")
    log(f"  固定大纲: {len(FIXED_OUTLINE)} 页")
    log()

    t0 = time.time()
    resp = requests.post(f"{BASE_URL}/api/generate-ppt-parallel", json={
        "pages": FIXED_OUTLINE,
        "topic": "产品战略发布会",
        "template": template_id,
        "save_pages": True,
        "progress_total": len(FIXED_OUTLINE),
    }, timeout=600)

    elapsed = time.time() - t0

    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert data.get("success"), f"生成失败: {data.get('error', 'unknown')}"

    log(f"  [PASS] 耗时: {elapsed:.0f}s")
    log(f"  页数: {data.get('page_count')}")
    log(f"  文档大小: {data.get('document_size', 0):,} 字符")

    slides = data.get("slides", [])
    log()
    log(f"  幻灯片详情 ({len(slides)} 页):")

    # 预期的 slide class 顺序
    expected_classes = [
        "cover", "toc",
        "section", "content", "content",
        "section", "content", "content",
        "ending",
    ]

    html = data.get("html", "")
    actual_classes = re.findall(r'class="slide\s+(\w+)"', html)

    log(f"  预期 class 顺序: {expected_classes}")
    log(f"  实际 class 顺序: {actual_classes}")

    # 验证
    assert len(actual_classes) == 9, \
        f"预期 9 个 slide，实际找到 {len(actual_classes)} 个"
    assert actual_classes == expected_classes, \
        f"slide class 不匹配!\n  预期: {expected_classes}\n  实际: {actual_classes}"

    for i, s in enumerate(slides):
        pn = s.get("page_number", "?")
        pt = s.get("page_type", "?")
        title = s.get("title", "")[:50]
        html_ok = "✓" if s.get("html") else "✗"
        log(f"    [{pn}] {pt:8s} | html={html_ok} | {title}")

    # 额外结构检查
    assert "slides-wrapper" in html, "缺少 slides-wrapper"
    assert "slides-track" in html, "缺少 slides-track"
    assert "nav-dots" in html, "缺少 nav-dots"
    assert "nav-arrows" in html, "缺少 nav-arrows"
    # 导航点必须由 JS 动态生成，HTML 中不应有硬编码的 nav-dot
    nav_dots_match = re.search(r'<div[^>]*id="navDots"[^>]*>(.*?)</div>', html, re.DOTALL)
    if nav_dots_match:
        inner = nav_dots_match.group(1).strip()
        hardcoded = re.findall(r'class="[^"]*nav-dot[^"]*"', inner)
        assert not hardcoded, f".nav-dots 内硬编码了导航点: {hardcoded}"

    log()
    log("  [PASS] PPT 结构验证通过")
    log("  [PASS] slide class 顺序正确")
    log("  [PASS] 导航结构完整")

    save_html("03_preview_ppt.html", html)
    save_json("04_preview_slides.json", slides)

    return data


# ============================================================
# Main
# ============================================================
def main():
    log("=" * 60)
    log("端到端测试: 模板生成 → PPT预览生成")
    log(f"输出目录: {OUTPUT_DIR}")
    log()

    assert check_backend(), "后端未启动，请先运行: python app.py"
    log("[INFO] 后端运行正常")
    log()

    ensure_output_dir()

    # 保存固定大纲供参考
    save_json("00_fixed_outline.json", {
        "description": "固定的大纲内容，不依赖LLM动态生成",
        "page_count": len(FIXED_OUTLINE),
        "pages": FIXED_OUTLINE,
    })

    # Step 1: 生成模板
    parsed = step1_generate_template()

    # Step 2: 保存模板
    template_id = step2_save_template(parsed)

    # Step 3: 生成预览PPT
    result = step3_generate_preview(template_id)

    log()
    log("=" * 60)
    log("全部通过!")
    log(f"  模板ID: {template_id}")
    log(f"  PPT页数: {result.get('page_count')}")
    log(f"  输出目录: {OUTPUT_DIR}")
    log("=" * 60)


if __name__ == "__main__":
    main()
