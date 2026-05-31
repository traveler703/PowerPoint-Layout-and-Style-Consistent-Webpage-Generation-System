"""
PPT 生成全流程测试脚本

流程: 解析文档 → 生成大纲 → 选择模板 → 生成PPT
每阶段输出保存到 test/output/ 目录
"""
import json
import os
import sys
import time
import threading
import requests

# 修复 Windows GBK 编码问题
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

BASE_URL = "http://127.0.0.1:5000"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TEST_FILE = os.path.join(os.path.dirname(__file__), "t.md")


def log(msg=""):
    """带 flush 的打印"""
    print(msg, flush=True)


def progress_spinner(stop_event, label="处理中"):
    """后台线程显示进度点"""
    dots = 0
    while not stop_event.is_set():
        dots = (dots + 1) % 4
        print(f"\r  {label}{'.' * dots}   ", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 50, end="\r", flush=True)  # 清除行


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "slides"), exist_ok=True)


def save_json(filename, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"  ✓ 已保存: {path}")
    return path


def save_html(filename, html):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = len(html.encode("utf-8")) / 1024
    log(f"  ✓ 已保存: {path} ({size_kb:.1f} KB)")
    return path


def step1_parse_document():
    """阶段1: 上传 t.md 并用 LLM 解析为结构化页面"""
    log("=" * 60)
    log("阶段1: 解析文档 (POST /api/parse-document)")
    log("=" * 60)

    if not os.path.exists(TEST_FILE):
        log(f"✗ 测试文件不存在: {TEST_FILE}")
        sys.exit(1)

    with open(TEST_FILE, "r", encoding="utf-8") as f:
        content_preview = f.read()[:200]
    log(f"  输入文件: {TEST_FILE}")
    log(f"  文件预览: {content_preview[:80]}...")

    with open(TEST_FILE, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/api/parse-document",
            files={"file": ("t.md", f, "text/markdown")},
            timeout=180,
        )

    if resp.status_code != 200:
        log(f"✗ 请求失败: {resp.status_code}")
        log(f"  响应: {resp.text[:500]}")
        sys.exit(1)

    data = resp.json()
    if not data.get("success"):
        log(f"✗ 解析失败: {data.get('error')}")
        sys.exit(1)

    result = data["result"]
    pages = result.get("pages", [])
    meta = data.get("meta", {})

    log(f"  标题: {result.get('title')}")
    log(f"  副标题: {result.get('subtitle')}")
    log(f"  页数: {len(pages)}")
    log(f"  解析方式: {'LLM' if meta.get('llm_parsed') else '规则'}")

    # 打印页面结构概览
    for i, p in enumerate(pages):
        ptype = p.get("type", "?")
        title = p.get("title", "")[:40]
        bullets = len(p.get("bullets", []) or [])
        items = len(p.get("items", []) or [])
        extra = f", bullets={bullets}" if bullets else ""
        extra += f", items={items}" if items else ""
        log(f"    [{i+1}] {ptype:8s} | {title}{extra}")

    save_json("01_parsed_result.json", data)
    return data


def step2_convert_to_generation_format(parsed_data):
    """阶段2: 将解析结果转换为生成API所需的格式"""
    log()
    log("=" * 60)
    log("阶段2: 转换页面格式 (前端 appStore.generatePagesFromParseResult 逻辑)")
    log("=" * 60)

    result = parsed_data["result"]
    pages = result.get("pages", [])

    # 转换为 /api/generate-ppt-parallel 需要的格式
    generation_pages = []
    for p in pages:
        gp = {
            "page_type": p.get("type", "content"),
            "title": p.get("title", ""),
            "subtitle": p.get("subtitle", ""),
            "summary": p.get("summary") or p.get("subtitle", ""),
            "bullets": p.get("bullets", []) or [],
        }
        # TOC: 将 items 作为 bullets
        if gp["page_type"] == "toc" and p.get("items"):
            gp["bullets"] = p["items"]
        generation_pages.append(gp)

    topic = result.get("title", "PPT演示文稿")

    payload = {
        "pages": generation_pages,
        "topic": topic,
        "template": "tech",
        "save_pages": True,
        "progress_total": len(generation_pages),
    }

    log(f"  主题: {topic}")
    log(f"  模板: tech")
    log(f"  转换页数: {len(generation_pages)}")
    for i, gp in enumerate(generation_pages):
        ptype = gp["page_type"]
        title = gp["title"][:40]
        bullets = len(gp["bullets"])
        log(f"    [{i+1}] {ptype:8s} | {title}{f', bullets={bullets}' if bullets else ''}")

    save_json("02_generation_payload.json", payload)
    return payload


def step3_generate_ppt(payload):
    """阶段3: 调用生成API生成完整PPT"""
    log()
    log("=" * 60)
    log("阶段3: 生成PPT (POST /api/generate-ppt-parallel)")
    log("=" * 60)

    log(f"  页数: {len(payload['pages'])}, 模板: {payload['template']}")
    log("  正在生成PPT（内容页 LLM 并行生成，约需 2-5 分钟）...")
    log()

    t_start = time.time()
    stop = threading.Event()
    spinner = threading.Thread(target=progress_spinner, args=(stop, "LLM生成中"), daemon=True)
    spinner.start()

    try:
        resp = requests.post(
            f"{BASE_URL}/api/generate-ppt-parallel",
            json=payload,
            timeout=600,
        )
    finally:
        stop.set()
        spinner.join(timeout=1)

    elapsed = time.time() - t_start

    if resp.status_code != 200:
        log(f"[失败] HTTP {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)

    data = resp.json()
    if not data.get("success"):
        log(f"[失败] {data.get('error')}")
        sys.exit(1)

    log(f"  耗时: {elapsed:.0f}s | 页数: {data.get('page_count')} | 大小: {data.get('document_size', 0):,} 字符")
    log(f"  输出: {data.get('output_path')}")

    # 打印页面布局概览
    for s in data.get("slides", []):
        log(f"    [幻灯片 {s.get('page_number')}] {s.get('page_type'):8s} | layout={s.get('layout_type', '-')} | {s.get('title', '')[:40]}")

    # 保存完整HTML
    html = data.get("html", "")
    if html:
        save_html("03_full_presentation.html", html)

    # 保存各幻灯片HTML
    slides = data.get("slides", [])
    for s in slides:
        slide_html = s.get("html", "")
        if slide_html:
            pnum = s.get("page_number", 0)
            ptype = s.get("page_type", "unknown")
            save_html(f"slides/{pnum:02d}_{ptype}.html", slide_html)

    # 保存生成结果元数据
    summary = {
        "elapsed_seconds": round(elapsed, 1),
        "page_count": data.get("page_count"),
        "document_size": data.get("document_size"),
        "output_path": data.get("output_path"),
        "slides": [
            {
                "page_number": s.get("page_number"),
                "page_type": s.get("page_type"),
                "layout_type": s.get("layout_type"),
                "title": s.get("title"),
                "page_url": s.get("page_url"),
            }
            for s in slides
        ],
    }
    save_json("04_generation_summary.json", summary)

    return data


def main():
    log("PPT 全流程测试")
    log(f"API地址: {BASE_URL}")
    log(f"输出目录: {OUTPUT_DIR}")
    log()

    # 检查后端是否运行
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        log(f"✓ 后端连接正常 (health: {r.status_code})")
    except requests.ConnectionError:
        log("✗ 无法连接到后端，请确保 Flask 已启动: python app.py")
        sys.exit(1)

    ensure_output_dir()

    # 阶段1: 解析文档
    parsed_data = step1_parse_document()

    # 阶段2: 转换格式
    gen_payload = step2_convert_to_generation_format(parsed_data)

    # 阶段3: 生成PPT
    gen_result = step3_generate_ppt(gen_payload)

    # 总结
    log()
    log("=" * 60)
    log("全部完成!")
    log("=" * 60)
    log(f"  输出目录: {OUTPUT_DIR}")
    log(f"  - 01_parsed_result.json      解析结果")
    log(f"  - 02_generation_payload.json  生成请求参数")
    log(f"  - 03_full_presentation.html   完整PPT HTML")
    log(f"  - 04_generation_summary.json  生成摘要")
    log(f"  - slides/                     各幻灯片HTML")
    log()
    log(f"  在浏览器打开: file:///{os.path.join(OUTPUT_DIR, '03_full_presentation.html')}")


if __name__ == "__main__":
    main()
