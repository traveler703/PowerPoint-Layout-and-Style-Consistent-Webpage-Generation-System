"""
LandPPT Demo - Flask应用
主入口文件（Pipeline 引擎）
"""
import asyncio
import json
import logging
import os
import queue
import re
import threading
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS
from config import APP_HOST, APP_PORT, DEBUG
from services.project_service import (
    ProjectService, OutlineService, GeneratedPptService
)
from scripts.template_generator import register_template_api_routes
from engine.content import parse_user_document
from engine.types import SemanticPageInput
from pipeline import run_pipeline
from bs4 import BeautifulSoup
from evaluator.layout_metrics import overlap_ratio_from_html
from evaluator.style_metrics import aggregate_color_deviation, color_consistency_from_html, extract_colors_from_html
from generator.llm_client import default_llm_client
from parsers import (
    extract_text_from_file,
    parse_document_to_json,
    parsed_json_to_outline,
    parsed_json_to_frontend_pages,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'landppt-demo-secret-key'
CORS(app)

MAX_LLM_INPUT_CHARS = 20000
SUPPORTED_DOCUMENT_EXTENSIONS = {".docx", ".pptx", ".txt", ".md", ".pdf"}


def _prepare_text_for_llm(text: str, max_chars: int = MAX_LLM_INPUT_CHARS) -> str:
    """压缩超长文本，避免触发模型上下文长度限制。"""
    if len(text) <= max_chars:
        return text

    head_chars = int(max_chars * 0.6)
    tail_chars = max_chars - head_chars
    clipped_text = (
        text[:head_chars]
        + "\n\n[... 中间内容已省略，系统已自动截断超长文本 ...]\n\n"
        + text[-tail_chars:]
    )
    return clipped_text


def _semantic_to_parse_result(text: str) -> dict:
    pages = parse_user_document(text)
    sections = []
    for sem in pages:
        bullets = sem.bullet_points or [b.title for b in sem.bullet_items if b.title]
        sections.append(
            {
                "title": sem.title or f"第{sem.page_index + 1}部分",
                "content": sem.summary or "",
                "bullets": bullets,
            }
        )

    title = next((p.title for p in pages if p.title), "") or "未命名文档"
    summary = next((p.summary for p in pages if p.summary), "") or ""
    return {"title": title, "summary": summary, "sections": sections}


def _slide_to_page_markdown(slide: dict) -> str:
    title = slide.get("title", "").strip() or "未命名页面"
    points = slide.get("content_points") or slide.get("bullets") or []
    lines = [f"# {title}"]
    subtitle = (slide.get("subtitle") or "").strip()
    if subtitle:
        lines.append(subtitle)
    for point in points:
        point_text = str(point).strip()
        if point_text:
            lines.append(f"- {point_text}")
    return "\n".join(lines)


def _outline_to_pipeline_input(outline: dict, fallback_title: str = "演示文稿") -> str:
    slides = outline.get("slides") or []
    if not slides:
        return f"# {fallback_title}"
    return "\n---\n".join(_slide_to_page_markdown(slide) for slide in slides)


def _build_outline_from_parse_result(parse_result: dict) -> dict:
    title = parse_result.get("title", "未命名文档")
    slides = [
        {
            "page_number": 1,
            "title": title,
            "content_points": [],
            "slide_type": "title",
        }
    ]
    for idx, section in enumerate(parse_result.get("sections", []), start=2):
        slides.append(
            {
                "page_number": idx,
                "title": section.get("title") or f"第{idx - 1}部分",
                "content_points": section.get("bullets", []),
                "slide_type": "content",
            }
        )
    return {"title": title, "slides": slides}


def _load_parsed_json_payload(data: dict) -> dict:
    parsed_json = data.get("parsed_json")
    if parsed_json:
        return parsed_json
    json_path = data.get("json_path") or data.get("output_json_path", "")
    if not json_path:
        raise ValueError("缺少 parsed_json 或 json_path / output_json_path")
    candidates = []
    if os.path.isabs(json_path):
        candidates.append(json_path)
    base = os.path.dirname(__file__)
    candidates.append(os.path.normpath(os.path.join(base, json_path)))
    candidates.append(os.path.join(base, "output", os.path.basename(json_path)))
    for c in candidates:
        if c and os.path.isfile(c):
            with open(c, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(f"找不到解析 JSON 文件: {json_path}")


def _load_page_html_from_outputs(page_number: int) -> tuple[str, str]:
    """按页码从 output/pages 加载页面 HTML，返回 (html, path)。"""
    import glob

    output_dir = os.path.join(os.path.dirname(__file__), "output", "pages")
    if not os.path.exists(output_dir):
        return "", ""
    for pattern in (f"{page_number:02d}_*.html", f"*{page_number}*.html"):
        for path in glob.glob(os.path.join(output_dir, pattern)):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read(), path
            except OSError:
                return "", path
    return "", ""


def _ensure_single_page_canvas_css(html: str) -> str:
    """Ensure saved per-page HTML keeps its 1280x720 slide canvas."""
    if not html or "landppt-single-page-canvas" in html:
        return html
    css = """
<style id="landppt-single-page-canvas">
.slides-track > .slide-container,
.slides-track > .slide-container > .slide-wrapper{width:1280px!important;height:720px!important;min-width:1280px!important;min-height:720px!important;flex:0 0 1280px!important;}
.slides-track > .slide-container > .slide-wrapper > .slide{width:1280px!important;height:720px!important;min-width:1280px!important;min-height:720px!important;}
</style>
"""
    if "</head>" in html:
        return html.replace("</head>", css + "\n</head>", 1)
    return css + html


def _resolve_output_html_path(output_path: str | None) -> str:
    """Resolve a user-provided output path inside the local output directory."""
    if not output_path:
        return ""
    base_output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "output"))
    candidate = output_path
    if not os.path.isabs(candidate):
        candidate = os.path.join(os.path.dirname(__file__), candidate)
    candidate = os.path.abspath(candidate)
    if not candidate.startswith(base_output_dir + os.sep):
        return ""
    if not candidate.lower().endswith(".html") or not os.path.isfile(candidate):
        return ""
    return candidate


def _extract_slide_from_html(html: str):
    """Extract the actual .slide node from a full page document or a slide fragment."""
    soup = BeautifulSoup(html or "", "html.parser")
    slide = soup.select_one(".slide-wrapper > .slide") or soup.select_one(".slides-track > .slide") or soup.select_one(".slide")
    return slide


def _update_presentation_file(output_path: str | None, page_number: int, page_html: str) -> tuple[str, str]:
    """Replace the selected slide inside the generated full presentation HTML file."""
    resolved_path = _resolve_output_html_path(output_path)
    if not resolved_path:
        return "", ""

    new_slide = _extract_slide_from_html(page_html)
    if not new_slide:
        return "", resolved_path

    with open(resolved_path, "r", encoding="utf-8") as f:
        presentation_html = f.read()

    soup = BeautifulSoup(presentation_html, "html.parser")
    track = soup.select_one("#slidesTrack, .slides-track")
    if not track:
        return "", resolved_path

    slide_nodes = [
        child for child in track.find_all(recursive=False)
        if getattr(child, "get", None)
        and (
            "slide" in (child.get("class") or [])
            or "slide-container" in (child.get("class") or [])
        )
    ]
    if page_number < 1 or page_number > len(slide_nodes):
        return "", resolved_path

    replacement = BeautifulSoup(str(new_slide), "html.parser")
    replacement_slide = replacement.select_one(".slide")
    if not replacement_slide:
        return "", resolved_path
    target = slide_nodes[page_number - 1]
    if "slide" in (target.get("class") or []):
        target.replace_with(replacement_slide)
    else:
        target_slide = target.select_one(".slide")
        if target_slide:
            target_slide.replace_with(replacement_slide)
        else:
            target.clear()
            target.append(replacement_slide)

    updated_html = str(soup)
    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write(updated_html)
    return updated_html, resolved_path


def _save_page_html_to_outputs(page_number: int, html: str) -> str:
    """将单页 HTML 写回 output/pages。"""
    output_dir = os.path.join(os.path.dirname(__file__), "output", "pages")
    os.makedirs(output_dir, exist_ok=True)
    _, existing_path = _load_page_html_from_outputs(page_number)
    target_path = existing_path or os.path.join(output_dir, f"{page_number:02d}_patched.html")
    html = _ensure_single_page_canvas_css(html)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(html)
    return target_path


def _bump_font_size_in_style(style: str, *, max_px: int = 18, step_px: int = 3) -> tuple[str, bool]:
    match = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", style or "", flags=re.I)
    if not match:
        return style, False
    current = float(match.group(1))
    next_size = min(current + step_px, max_px)
    if next_size <= current:
        return style, False
    next_value = f"{int(next_size) if next_size.is_integer() else next_size:g}px"
    next_style = style[:match.start(1)] + next_value[:-2] + style[match.end(1):]
    return next_style, True


def _try_apply_common_font_resize(soup: BeautifulSoup, instruction: str) -> list[dict]:
    """Handle simple local font-size requests with narrow selectors before asking the LLM."""
    normalized = instruction.replace(" ", "")
    wants_bigger_font = (
        ("字号" in normalized or "字体大小" in normalized or "font-size" in normalized.lower())
        and any(word in normalized for word in ("调大", "变大", "放大", "大一点", "增大"))
    )
    wants_top_bottom = any(word in normalized for word in ("上下", "上、下", "上和下", "顶部和底部"))
    if not (wants_bigger_font and wants_top_bottom):
        return []

    page_content = soup.select_one(".page-content")
    if not page_content:
        return []

    candidates = []
    for node in page_content.find_all(["div", "span", "p"]):
        text = node.get_text(" ", strip=True)
        style = node.get("style") or ""
        if len(text) >= 16 and re.search(r"font-size\s*:\s*\d", style, flags=re.I):
            candidates.append((node, text))

    if not candidates:
        return []

    targets = []
    for node, _ in (candidates[0], candidates[-1]):
        if node not in targets:
            targets.append(node)

    operations = []
    for node in targets:
        next_style, changed = _bump_font_size_in_style(node.get("style") or "")
        if not changed:
            continue
        node["style"] = next_style
        operations.append(
            {
                "type": "update_style",
                "selector": "matched .page-content long text block",
                "style": {"font-size": re.search(r"font-size\s*:\s*([^;]+)", next_style, flags=re.I).group(1).strip()},
            }
        )
    return operations


def _json_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _build_outline_from_pages_data(pages_data: list[dict], topic: str) -> dict:
    """把前端扁平页面列表转换为 pipeline outline。"""
    title = topic
    subtitle = ""
    date_badge = ""
    toc_items = []
    include_toc = False
    include_ending = False
    ending_title = "谢谢观看"
    ending_message = ""
    sections = []
    current_section = None

    for p in pages_data:
        page_type = p.get("page_type", "content")
        if page_type == "cover":
            title = p.get("title", title)
            subtitle = p.get("subtitle", "")
            date_badge = p.get("date_badge", "")
        elif page_type == "toc":
            include_toc = True
            raw_items = p.get("bullets") or p.get("items") or p.get("content_points") or []
            toc_items = [
                {"title": str(item).strip(), "description": ""}
                for item in raw_items
                if str(item).strip()
            ]
        elif page_type in ("end", "ending"):
            include_ending = True
            ending_title = p.get("title") or "谢谢观看"
            ending_message = p.get("subtitle") or p.get("summary") or ""
            continue
        elif page_type == "section":
            current_section = {
                "title": p.get("subtitle") or p.get("title") or "章节",
                "content_pages": [],
                "include_section_page": True,
            }
            sections.append(current_section)
        elif page_type == "content":
            if not sections:
                current_section = {
                    "title": "主要内容",
                    "content_pages": [],
                    "include_section_page": False,
                }
                sections.append(current_section)
            summary = p.get("summary") or p.get("subtitle", "")
            bullets = p.get("bullets", []) or []
            if not bullets and summary:
                bullets = [summary[:400]]
            sections[-1]["content_pages"].append(
                {
                    "title": p.get("title", ""),
                    "summary": summary,
                    "bullets": bullets,
                }
            )

    if not sections:
        sections = [
            {
                "title": "主要内容",
                "include_section_page": False,
                "content_pages": [
                    {
                        "title": title or "概述",
                        "summary": subtitle,
                        "bullets": [subtitle] if subtitle else ["请提供有效内容以生成正文要点。"],
                    }
                ],
            }
        ]

    return {
        "title": title,
        "subtitle": subtitle,
        "date_badge": date_badge,
        "toc_items": toc_items,
        "include_toc": include_toc,
        "include_ending": include_ending,
        "ending_title": ending_title,
        "ending_message": ending_message,
        "sections": sections,
    }


def _presentation_result_payload(result) -> dict:
    html_content = ""
    if result.success and result.output_path:
        with open(result.output_path, "r", encoding="utf-8") as f:
            html_content = f.read()

    pages_dir = os.path.join(os.path.dirname(result.output_path), "pages") if result.output_path else ""
    slides = []
    for i, layout in enumerate(result.page_layouts):
        page_num = layout.get("page_number", i + 1)
        page_html = result.pages_html[i] if i < len(result.pages_html) else ""
        page_url = ""
        page_path = ""
        if getattr(result, "page_paths", None) and i < len(result.page_paths):
            page_path = result.page_paths[i]
        if page_path and os.path.isfile(page_path):
            page_url = f"/output/pages/{os.path.basename(page_path)}"
            with open(page_path, "r", encoding="utf-8") as pf:
                page_html = pf.read()
        elif pages_dir and os.path.isdir(pages_dir):
            prefix = f"{int(page_num):02d}_{layout.get('type', '')}_"
            fallback_prefix = f"{int(page_num):02d}_"
            matches = [
                name for name in os.listdir(pages_dir)
                if name.startswith(prefix) and name.endswith(".html")
            ] or [
                name for name in os.listdir(pages_dir)
                if name.startswith(fallback_prefix) and name.endswith(".html")
            ]
            if matches:
                newest = max(matches, key=lambda name: os.path.getmtime(os.path.join(pages_dir, name)))
                page_url = f"/output/pages/{newest}"
                with open(os.path.join(pages_dir, newest), "r", encoding="utf-8") as pf:
                    page_html = pf.read()
        slides.append(
            {
                "page_type": layout.get("type", "content"),
                "title": layout.get("title", ""),
                "layout_type": layout.get("layout_type", ""),
                "page_number": page_num,
                "page_url": page_url,
                "html": page_html,
            }
        )

    return {
        "success": result.success,
        "html": html_content,
        "slides": slides,
        "page_count": result.page_count,
        "document_size": result.document_size,
        "output_path": result.output_path,
        "error": result.error,
    }


@app.route('/')
def index():
    """首页"""
    import os
    index_path = os.path.join(os.path.dirname(__file__), 'index.html')
    return send_file(index_path)


@app.route('/api/parse-text', methods=['POST'])
def parse_text():
    """解析文本内容API - 使用LLM智能解析"""
    import asyncio
    try:
        data = request.get_json()
        
        text = data.get('text', '')
        project_id = data.get('project_id')

        head = text.lstrip()[:16]
        if head.startswith("%PDF") or "\x00" in text[:8192]:
            return jsonify(
                {
                    "error": "检测到 PDF 或其它二进制内容。请切换到「上传文件」并上传 PDF，由服务器解析；勿将 PDF 以文本方式粘贴。",
                }
            ), 400
        if text.startswith("PK\x03\x04"):
            return jsonify(
                {
                    "error": "检测到 Word/Office 压缩包格式（.docx 等）。请使用「上传文件」上传原文件，勿粘贴二进制内容。",
                }
            ), 400
        
        if not text or len(text.strip()) < 10:
            return jsonify({'error': '文本内容太少，至少需要10个字符'}), 400
        
        original_len = len(text)
        logger.info(
            f"解析文本: 原始长度={original_len}字符, project_id={project_id}"
        )
        
        # 使用 LLM 智能解析
        from generator.prompts import (
            build_document_parsing_prompt,
            parse_document_parsing_response,
        )
        from generator.llm_client import default_llm_client
        
        llm_client = default_llm_client()
        system_prompt, user_prompt = build_document_parsing_prompt(text)
        
        logger.info("调用 LLM 解析文档结构...")
        response = asyncio.run(llm_client.complete(system_prompt, user_prompt))
        
        parse_result = parse_document_parsing_response(response)
        
        # 直接使用 pages 数组格式（扁平的一页页结构）
        pages = parse_result.get('pages', [])
        
        # 如果没有识别到页面，创建一个默认页面
        if not pages:
            pages = [
                {"type": "cover", "title": parse_result.get('title', 'PPT演示文稿'), "subtitle": parse_result.get('subtitle', '')},
                {"type": "end", "title": "谢谢观看", "subtitle": ""}
            ]
        
        result = {
            'title': parse_result.get('title', '未命名文档'),
            'subtitle': parse_result.get('subtitle', ''),
            'pages': pages
        }
        
        logger.info(f"LLM解析完成: title={result.get('title')}, pages={len(pages)}")
        logger.info(f"LLM原始响应: {response[:500]}...")

        return jsonify({
            'success': True,
            'result': result,
            'meta': {
                'original_text_length': original_len,
                'llm_parsed': True
            }
        })

    except Exception as e:
        logger.error(f"解析文本失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/parse-document', methods=['POST'])
def parse_document():
    """上传并解析文档：规则解析器提取纯文本，LLM 负责页面结构分析。"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "缺少上传文件(file)"}), 400

        upload = request.files["file"]
        if not upload or not upload.filename:
            return jsonify({"error": "文件名为空"}), 400

        ext = Path(upload.filename).suffix.lower()
        if ext not in SUPPORTED_DOCUMENT_EXTENSIONS:
            return jsonify({"error": f"仅支持: {', '.join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))}"}), 400

        upload_dir = os.path.join(os.path.dirname(__file__), "output", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"{int(time.time())}_{os.path.basename(upload.filename)}"
        uploaded_path = os.path.join(upload_dir, safe_name)
        upload.save(uploaded_path)

        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)

        raw_text = extract_text_from_file(uploaded_path)
        if not raw_text.strip():
            return jsonify({"error": "未能从文件中提取到可解析文本"}), 400

        extracted_text_path = os.path.join(output_dir, f"extracted_{int(time.time())}.txt")
        with open(extracted_text_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
        rel_text = os.path.relpath(extracted_text_path, os.path.dirname(__file__)).replace("\\", "/")

        from generator.prompts import (
            build_document_parsing_prompt,
            parse_document_parsing_response,
        )

        llm_text = _prepare_text_for_llm(raw_text)
        llm_client = default_llm_client()
        system_prompt, user_prompt = build_document_parsing_prompt(llm_text)
        logger.info("调用 LLM 解析上传文档结构...")
        response = asyncio.run(llm_client.complete(system_prompt, user_prompt))
        parse_result = parse_document_parsing_response(response)
        frontend_pages = parse_result.get("pages", [])
        if not frontend_pages:
            frontend_pages = [
                {"type": "cover", "title": parse_result.get("title") or Path(upload.filename).stem, "subtitle": parse_result.get("subtitle", "")},
                {"type": "end", "title": "谢谢观看", "subtitle": ""},
            ]
        result = {
            "title": parse_result.get("title") or Path(upload.filename).stem or "未命名文档",
            "subtitle": parse_result.get("subtitle", ""),
            "pages": frontend_pages,
            "extracted_text_path": rel_text,
            "source_file": uploaded_path,
        }

        logger.info(
            f"文档解析完成: file={upload.filename}, pages={len(frontend_pages)}, text_chars={len(raw_text)}"
        )
        return jsonify(
            {
                "success": True,
                "result": result,
                "meta": {
                    "llm_parsed": True,
                    "text_extracted": True,
                    "extracted_text_path": rel_text,
                    "extracted_text_abs": extracted_text_path,
                    "original_text_length": len(raw_text),
                    "llm_input_length": len(llm_text),
                },
            }
        )
    except Exception as e:
        logger.error(f"解析文档失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/outline-from-parsed-json', methods=['POST'])
def outline_from_parsed_json():
    """根据解析后的 JSON 构建生成引擎可用的大纲。"""
    try:
        data = request.get_json() or {}
        parsed_json = _load_parsed_json_payload(data)
        outline = parsed_json_to_outline(parsed_json)
        return jsonify({"success": True, "outline": outline})
    except Exception as e:
        logger.error(f"构建大纲失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/generate-from-parsed-json', methods=['POST'])
def generate_from_parsed_json():
    """直接从解析 JSON 生成演示文稿。"""
    try:
        data = request.get_json() or {}
        parsed_json = _load_parsed_json_payload(data)
        template_name = data.get("template", "tech")
        output_filename = data.get("output_filename", f"from_parsed_{int(time.time())}.html")
        save_pages = bool(data.get("save_pages", True))

        outline = parsed_json_to_outline(parsed_json)
        from pipeline import PresentationGenerator
        generator = PresentationGenerator(template_name=template_name)
        result = asyncio.run(
            generator.generate_presentation(
                outline=outline,
                output_filename=output_filename,
                navigation=True,
                save_pages=save_pages,
            )
        )

        return jsonify(
            {
                "success": result.success,
                "output_path": result.output_path,
                "page_count": result.page_count,
                "document_size": result.document_size,
                "page_layouts": result.page_layouts,
                "error": result.error,
            }
        )
    except Exception as e:
        logger.error(f"从解析JSON生成失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/save-parse-result', methods=['POST'])
def save_parse_result():
    """保存解析结果到数据库"""
    try:
        data = request.get_json()

        project_id = data.get('project_id')
        parse_result = data.get('parse_result')

        if not project_id:
            return jsonify({'error': '项目ID不能为空'}), 400
        if not parse_result:
            return jsonify({'error': '解析结果不能为空'}), 400

        logger.info(f"保存解析结果: project_id={project_id}")

        original_text = data.get('original_text', '')

        ProjectService.update_project(project_id,
            parse_title=parse_result.get('title', '未命名文档'),
            parse_summary=parse_result.get('summary', ''),
            parse_sections=json.dumps(parse_result.get('sections', []), ensure_ascii=False),
            parse_original_text=original_text,
            page_count=len(parse_result.get('sections', [])) + 1
        )

        logger.info(f"解析结果保存成功: project_id={project_id}")

        return jsonify({
            'success': True,
            'message': '解析结果已保存'
        })

    except Exception as e:
        logger.error(f"保存解析结果失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/get-parse-result/<int:project_id>', methods=['GET'])
def get_parse_result(project_id):
    """获取项目的解析结果"""
    try:
        project = ProjectService.get_project(project_id)

        if not project:
            return jsonify({'error': '项目不存在'}), 404

        parse_result = {
            'title': project.get('parse_title', ''),
            'summary': project.get('parse_summary', ''),
            'sections': [],
            'original_text': project.get('parse_original_text', '')
        }

        sections_json = project.get('parse_sections', '[]')
        if sections_json:
            try:
                parse_result['sections'] = json.loads(sections_json)
            except:
                parse_result['sections'] = []

        return jsonify({
            'success': True,
            'result': parse_result
        })

    except Exception as e:
        logger.error(f"获取解析结果失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-outline', methods=['POST'])
def generate_outline():
    """生成大纲API"""
    try:
        data = request.get_json()
        
        topic = data.get('topic', '')
        if not topic:
            return jsonify({'error': '主题不能为空'}), 400
        
        logger.info(f"生成大纲: topic={topic[:50]}...")
        parse_result = _semantic_to_parse_result(topic)
        outline = _build_outline_from_parse_result(parse_result)
        
        return jsonify({
            'success': True,
            'outline': outline
        })
        
    except Exception as e:
        logger.error(f"生成大纲失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-ppt-parallel', methods=['POST'])
def generate_ppt_parallel():
    """并行生成PPT - 一次性返回所有页面（适合非流式场景）

    请求格式:
    {
        "pages": [
            {"page_type": "cover", "title": "...", "subtitle": "..."},
            {"page_type": "section", "title": "章节1", "subtitle": "..."},
            {"page_type": "content", "title": "...", "bullets": [...]},
            ...
        ],
        "topic": "PPT标题",
        "template": "tech",
        "save_pages": true
    }

    返回格式:
    {
        "success": true,
        "html": "完整HTML",
        "slides": [
            {"page_number": 1, "page_type": "cover", "title": "...", "html": "..."},
            ...
        ],
        "page_count": 14,
        "document_size": 12345
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        pages_data = data.get('pages', [])
        topic = data.get('topic', 'PPT演示文稿')
        template_name = data.get('template', 'tech')
        save_pages = data.get('save_pages', False)

        if not pages_data:
            return jsonify({'error': 'pages 数组不能为空'}), 400

        logger.info(f"[Parallel] 收到并行生成请求: {len(pages_data)} 页")

        # 解析 pages 为 sections 格式
        title = topic
        subtitle = ""
        date_badge = ""
        toc_items = []
        include_toc = False
        include_ending = False
        ending_title = "谢谢观看"
        ending_message = ""
        sections = []
        current_section = None

        for p in pages_data:
            page_type = p.get('page_type', 'content')
            if page_type == 'cover':
                title = p.get('title', title)
                subtitle = p.get('subtitle', '')
                date_badge = p.get('date_badge', '')
            elif page_type == 'toc':
                include_toc = True
                raw_items = p.get('bullets') or p.get('items') or p.get('content_points') or []
                toc_items = [
                    {'title': str(item).strip(), 'description': ''}
                    for item in raw_items
                    if str(item).strip()
                ]
            elif page_type in ('end', 'ending'):
                include_ending = True
                ending_title = p.get('title') or '谢谢观看'
                ending_message = p.get('subtitle') or p.get('summary') or ''
                continue
            elif page_type == 'section':
                current_section = {
                    'title': p.get('subtitle', p.get('title', '')),
                    'content_pages': [],
                    'include_section_page': True,
                }
                sections.append(current_section)
            elif page_type == 'content':
                if not sections:
                    current_section = {
                        'title': '默认章节',
                        'content_pages': [],
                        'include_section_page': False,
                    }
                    sections.append(current_section)
                summary = p.get('summary') or p.get('subtitle', '')
                bullets = p.get('bullets', []) or []
                if not bullets and summary:
                    bullets = [summary[:400]]
                sections[-1]['content_pages'].append({
                    'title': p.get('title', ''),
                    'summary': summary,
                    'bullets': bullets,
                })

        if not sections:
            flat_content = [p for p in pages_data if p.get('page_type') == 'content']
            if flat_content:
                sections = [
                    {
                        'title': '主要内容',
                        'include_section_page': False,
                        'content_pages': [
                            {
                                'title': x.get('title', ''),
                                'summary': x.get('summary') or x.get('subtitle', ''),
                                'bullets': x.get('bullets', [])
                                or ([(x.get('summary') or x.get('subtitle') or '')[:400]]),
                            }
                            for x in flat_content
                        ],
                    }
                ]
            else:
                sections = [
                    {
                        'title': '主要内容',
                        'include_section_page': False,
                        'content_pages': [
                            {
                                'title': title or '概述',
                                'summary': subtitle,
                                'bullets': [subtitle] if subtitle else ['请重新解析文档或上传有效文件以生成正文要点。'],
                            }
                        ],
                    }
                ]

        # 构建 outline
        outline = {
            'title': title,
            'subtitle': subtitle,
            'date_badge': date_badge,
            'toc_items': toc_items,
            'include_toc': include_toc,
            'include_ending': include_ending,
            'ending_title': ending_title,
            'ending_message': ending_message,
            'sections': sections
        }

        # 调用并行生成器
        from pipeline import PresentationGenerator
        generator = PresentationGenerator(template_name=template_name)
        output_filename = f"parallel_{int(time.time())}.html"


        result = asyncio.run(generator.generate_presentation(
            outline=outline,
            output_filename=output_filename,
            navigation=True,
            save_pages=save_pages,
        ))


        logger.info(f"[Parallel] 生成完成: {result.page_count} 页, {result.document_size} chars")
        return jsonify(_presentation_result_payload(result))

    except Exception as e:
        logger.error(f"并行生成PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-ppt-progress', methods=['POST'])
def generate_ppt_progress():
    """流式生成 PPT，按 NDJSON 持续返回进度和最终结果。"""
    data = request.get_json() or {}
    pages_data = data.get("pages", [])
    topic = data.get("topic", "PPT演示文稿")
    template_name = data.get("template", "tech")
    save_pages = data.get("save_pages", False)

    if not pages_data:
        return jsonify({"error": "pages 数组不能为空"}), 400

    def stream():
        events: queue.Queue[dict] = queue.Queue()

        def worker():
            try:
                from pipeline import PresentationGenerator

                outline = _build_outline_from_pages_data(pages_data, topic)
                generator = PresentationGenerator(template_name=template_name)
                output_filename = f"parallel_{int(time.time())}.html"
                completed_pages: set[int] = set()
                progress_total = (
                    1
                    + (1 if outline.get("include_toc") else 0)
                    + sum(1 for s in outline.get("sections", []) if s.get("include_section_page", True))
                    + sum(len(s.get("content_pages", [])) for s in outline.get("sections", []))
                    + (1 if outline.get("include_ending") else 0)
                )

                def progress_callback(current, total, page_info=None):
                    page_info = page_info or {}
                    page_number = int(page_info.get("page_number") or current or 0)
                    if page_number:
                        completed_pages.add(page_number)
                    if page_info.get("html"):
                        events.put(
                            {
                                "type": "slide",
                                "slide": {
                                    "page_number": page_number,
                                    "page_type": page_info.get("page_type", "content"),
                                    "title": page_info.get("title", ""),
                                    "layout_type": page_info.get("layout_type", ""),
                                    "html": page_info.get("html", ""),
                                    "evaluation": {
                                        "quality_warnings": page_info.get("quality_warnings", []),
                                    },
                                },
                            }
                        )
                    events.put(
                        {
                            "type": "progress",
                            "current": min(len(completed_pages), total),
                            "total": total,
                            "page": page_info,
                        }
                    )

                events.put({"type": "progress", "current": 0, "total": progress_total, "page": {"status": "started"}})
                result = asyncio.run(
                    generator.generate_presentation(
                        outline=outline,
                        output_filename=output_filename,
                        navigation=True,
                        save_pages=save_pages,
                        progress_callback=progress_callback,
                    )
                )
                payload = _presentation_result_payload(result)
                events.put({"type": "complete", "result": payload})
            except Exception as exc:
                logger.error(f"流式生成PPT失败: {exc}")
                events.put({"type": "error", "error": str(exc)})
            finally:
                events.put({"type": "done"})

        threading.Thread(target=worker, daemon=True).start()

        while True:
            event = events.get()
            if event.get("type") == "done":
                break
            yield _json_line(event)

    return Response(stream_with_context(stream()), mimetype="application/x-ndjson")


@app.route('/api/generate-preview', methods=['POST'])
def generate_preview():
    """生成单页预览"""
    try:
        data = request.get_json()
        
        slide_data = data.get('slide_data', {})
        page_number = data.get('page_number', 1)
        total_pages = data.get('total_pages', 1)
        if not slide_data:
            return jsonify({'error': '幻灯片数据不能为空'}), 400
        
        logger.info(f"生成预览: page={page_number}/{total_pages}")
        page_text = _slide_to_page_markdown(slide_data)
        html, report = asyncio.run(run_pipeline(page_text, output_format="html"))
        return jsonify({
            'success': True,
            'html': html,
            'evaluation': report.model_dump(),
            'page_number': page_number,
            'total_pages': total_pages
        })
        
    except Exception as e:
        logger.error(f"生成预览失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rewrite-slide', methods=['POST'])
def rewrite_slide():
    """根据用户指令重写选中的单页。"""
    try:
        data = request.get_json() or {}
        page = data.get("page") or {}
        instruction = (data.get("instruction") or "").strip()
        project_id = data.get("project_id")
        output_path = data.get("output_path") or data.get("presentation_output_path")

        if not page:
            return jsonify({"error": "页面数据不能为空"}), 400
        if not instruction:
            return jsonify({"error": "修改指令不能为空"}), 400

        page_id = page.get("id")
        page_number = int(page.get("page_number") or page.get("pageNumber") or 1)
        page_html = page.get("html") or ""
        if not page_html:
            page_html, _ = _load_page_html_from_outputs(page_number)

        title = (page.get("title") or "").strip() or f"第{page_number}页"
        system_prompt = (
            "你是专业的PPT单页修改助手。请根据用户指令修改当前页面，只输出严格JSON。"
            "优先返回可应用到现有HTML的局部操作，不要影响其它页面。"
            "只修改用户明确提到的元素；如果用户说上下两块文字，通常指页面内容区顶部说明文字和底部提示文字，不要改中间卡片、流程节点或标题。"
            "JSON格式："
            '{"page_id": 页面ID, "operations": ['
            '{"type": "update_style|delete_element|move_element", "selector": "CSS选择器", '
            '"style": {"CSS属性": "值"}, "position": "left|right|center|top|bottom"}], '
            '"page_data": {"title": "可选", "subtitle": "可选", "bullets": []}}'
        )
        user_prompt = json.dumps(
            {
                "project_id": project_id,
                "page": {
                    "id": page_id,
                    "page_number": page_number,
                    "title": title,
                    "html": page_html,
                },
                "instruction": instruction,
            },
            ensure_ascii=False,
        )

        raw = asyncio.run(default_llm_client().complete(system_prompt, user_prompt))
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]
        result = json.loads(cleaned)

        merged_page = dict(page)
        page_data = result.get("page_data") or {}
        if isinstance(page_data, dict):
            merged_page.update(page_data)

        soup = BeautifulSoup(page_html or "<div></div>", "html.parser")
        operations = result.get("operations") or []

        def merge_style(node, updates: dict):
            style_map = {}
            for chunk in (node.get("style") or "").split(";"):
                if ":" in chunk:
                    k, v = chunk.split(":", 1)
                    style_map[k.strip()] = v.strip()
            style_map.update({str(k): str(v) for k, v in updates.items()})
            node["style"] = "; ".join(f"{k}: {v}" for k, v in style_map.items())

        for op in operations:
            if not isinstance(op, dict):
                continue
            selector = op.get("selector") or ""
            try:
                nodes = soup.select(selector) if selector else []
            except Exception:
                nodes = []
            if not nodes:
                continue

            op_type = str(op.get("type") or "").lower()
            if op_type == "delete_element":
                for node in nodes:
                    node.decompose()
            elif op_type in ("update_style", "move_element"):
                style_updates = op.get("style") if isinstance(op.get("style"), dict) else {}
                position = str(op.get("position") or "").lower()
                if position in {"left", "center", "right"}:
                    style_updates = {**style_updates, "text-align": position}
                elif position == "top":
                    style_updates = {**style_updates, "justify-content": "flex-start"}
                elif position == "bottom":
                    style_updates = {**style_updates, "justify-content": "flex-end"}
                for node in nodes:
                    merge_style(node, style_updates)

        quick_operations = _try_apply_common_font_resize(soup, instruction)
        combined_operations = [*operations, *quick_operations]
        html = _ensure_single_page_canvas_css(str(soup))
        saved_path = _save_page_html_to_outputs(page_number, html)
        presentation_html, updated_output_path = _update_presentation_file(output_path, page_number, html)
        result["page_id"] = page_id
        result["page_data"] = merged_page
        result["operations"] = combined_operations
        result["output_path"] = updated_output_path or output_path

        return jsonify(
            {
                "success": True,
                "result": result,
                "operations": combined_operations,
                "page_data": merged_page,
                "html": html,
                "presentation_html": presentation_html,
                "output_path": updated_output_path or output_path,
                "saved_path": saved_path,
            }
        )
    except Exception as e:
        logger.error(f"重写页面失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/evaluate-presentation', methods=['POST'])
def evaluate_presentation():
    """评估生成后的 HTML 演示文稿，返回报告页使用的数据。"""
    try:
        data = request.get_json() or {}
        slides = data.get("slides") or []
        total_generation_time = float(data.get("total_generation_time") or 0)
        template_name = data.get("template") or "tech"

        if not slides:
            return jsonify({"error": "缺少 slides 数据"}), 400

        try:
            template = __import__("templates.template_loader", fromlist=["load_template"]).load_template(template_name)
            css_variables = dict(template.css_variables)
            for idx, color in enumerate(sorted(extract_colors_from_html(template.raw_html))):
                css_variables[f"template-color-{idx}"] = color
        except Exception:
            css_variables = {}

        pages = []
        style_metrics = []
        for idx, slide in enumerate(slides, start=1):
            html = slide.get("html") or ""
            layout = overlap_ratio_from_html(html)
            style = color_consistency_from_html(html, css_variables)
            style_metrics.append(style)
            overlap_ok = layout.overlap_ratio == 0
            color_ok = (style.global_color_deviation_percent or 0) <= 5
            pages.append(
                {
                    "page_number": slide.get("pageNumber") or slide.get("page_number") or idx,
                    "title": slide.get("title") or f"第{idx}页",
                    "overlap_ratio": layout.overlap_ratio,
                    "color_deviation_percent": style.global_color_deviation_percent,
                    "passed": overlap_ok and color_ok,
                }
            )

        global_color_deviation = aggregate_color_deviation(style_metrics)
        page_count = len(slides)
        average_generation_time = total_generation_time / page_count if total_generation_time and page_count else 0
        passed = all(p["overlap_ratio"] == 0 for p in pages) and global_color_deviation <= 5

        summary = ""
        try:
            prompt = json.dumps(
                {
                    "task": "用中文简短评估HTML演示文稿质量",
                    "constraints": {
                        "overlap_ratio_target": 0,
                        "global_color_deviation_percent_target": "<=5",
                    },
                    "metrics": {
                        "page_count": page_count,
                        "global_color_deviation_percent": global_color_deviation,
                        "average_generation_time_seconds": average_generation_time,
                        "pages": pages,
                    },
                },
                ensure_ascii=False,
            )
            summary = asyncio.run(default_llm_client().complete("只输出一段中文评估摘要。", prompt))
        except Exception as llm_err:
            logger.warning(f"LLM评估摘要失败，使用本地摘要: {llm_err}")
            summary = "已完成规则评估。请重点关注重叠率不为 0 或颜色偏差超过 5% 的页面。"

        return jsonify(
            {
                "success": True,
                "report": {
                    "passed": passed,
                    "page_count": page_count,
                    "pages": pages,
                    "global_color_deviation_percent": global_color_deviation,
                    "average_generation_time_seconds": average_generation_time,
                    "summary": summary.strip(),
                    "metric_notes": {
                        "color_deviation": "每页色彩偏差率=该页中偏离模板调色板的颜色数量占比；全局色彩偏差率=各页色彩偏差率的平均值。",
                        "overlap_ratio": "元素重叠率基于内联绝对定位元素的矩形交叠面积估算，并忽略背景层、低透明度装饰和 pointer-events:none 的装饰元素。",
                    },
                },
            }
        )
    except Exception as e:
        logger.error(f"评估演示文稿失败: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/regenerate-page', methods=['POST'])
def regenerate_page():
    """重新生成单个内容页"""
    try:
        data = request.get_json() or {}
        page_data = data.get('page') or {}
        page_number = data.get('page_number', 1)
        template_name = data.get('template', 'tech')

        if not page_data:
            return jsonify({'error': '页面数据不能为空'}), 400

        logger.info(f"重新生成页面: page={page_number}, title={page_data.get('title', '')}")

        # 构建 SemanticPageInput
        from engine.types import SemanticPageInput
        from pipeline import PresentationGenerator
        from generator.prompts.content_html import generate_color_scheme_from_template
        from templates.template_loader import load_template as _load_template

        sem_page = SemanticPageInput(
            page_index=page_number - 1,
            title=page_data.get('title', ''),
            summary=page_data.get('summary') or page_data.get('subtitle', ''),
            page_type='content',
            bullet_points=page_data.get('bullets', []) or [],
            description=page_data.get('description') or None,
            highlights=page_data.get('highlights'),
            steps=page_data.get('steps'),
            compare=page_data.get('compare'),
        )

        # 用 pipeline 重新生成内容页 HTML
        gen = PresentationGenerator(template_name=template_name)
        await_gen = asyncio.run(gen.initialize())

        # 单页生成（两阶段）
        html_fragment, layout_info = asyncio.run(gen.generate_content_page_html(sem_page))

        # 包装为完整页面（与 _save_individual_pages 一致）
        skeleton = gen.renderer.render_content_page(
            title=page_data.get('title', ''),
            content=html_fragment,
            bullets=None,
            page_number=page_number,
            total_pages=data.get('total_pages', page_number),
        )
        standalone_html = gen.render_standalone_page(skeleton, page_number)

        # 与 _save_individual_pages 保持一致的后处理
        standalone_html = standalone_html.replace("{{TOTAL_PAGES}}", str(data.get('total_pages', page_number)))
        standalone_html = standalone_html.replace('<div class="nav-dots"', '<div class="nav-dots" style="display:none"')
        standalone_html = standalone_html.replace('<div class="nav-arrows">', '<div class="nav-arrows" style="display:none">')
        standalone_html = standalone_html.replace('<div class="page-indicator"', '<div class="page-indicator" style="display:none"')

        # 替换 output/pages 中的旧文件
        pages_dir = os.path.join(os.path.dirname(__file__), 'output', 'pages')
        if os.path.exists(pages_dir):
            import re as _re
            prefix = f"{page_number:02d}_"
            for fname in os.listdir(pages_dir):
                if fname.startswith(prefix):
                    old_path = os.path.join(pages_dir, fname)
                    os.remove(old_path)
                    logger.info(f"删除旧页面文件: {fname}")

        # 写入新文件
        os.makedirs(pages_dir, exist_ok=True)
        safe_title = _re.sub(r'[<>:"/\\|?*]', '_', page_data.get('title', '')[:20])
        new_filename = f"{page_number:02d}_{template_name}_content_{safe_title}.html"
        new_path = os.path.join(pages_dir, new_filename)
        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(standalone_html)

        logger.info(f"重新生成完成: page={page_number}, layout={layout_info.get('layout_type', '?')}")

        return jsonify({
            'success': True,
            'page_number': page_number,
            'html': standalone_html,
            'layout_type': layout_info.get('layout_type', ''),
        })

    except Exception as e:
        logger.error(f"重新生成页面失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/output/<path:filename>')
def serve_output(filename):
    """实验性：提供output文件夹的静态文件访问"""
    import os
    from urllib.parse import unquote
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    # 解码URL编码的文件名
    decoded_filename = unquote(filename)
    file_path = os.path.join(output_dir, decoded_filename)
    logger.info(f"请求文件: {file_path}")
    if not os.path.exists(file_path):
        return jsonify({'error': '文件不存在', 'path': file_path}), 404
    return send_file(file_path)


@app.route('/api/pages')
def list_pages():
    """列出pages目录下的所有HTML文件"""
    import os
    import glob
    pages_dir = os.path.join(os.path.dirname(__file__), 'output', 'pages')
    if not os.path.exists(pages_dir):
        return jsonify({'files': []})
    files = glob.glob(os.path.join(pages_dir, '*.html'))
    file_names = [os.path.basename(f) for f in files]
    return jsonify({'files': file_names})


@app.route('/api/page-content')
def get_page_content():
    """获取指定页面的HTML内容"""
    import os
    from urllib.parse import unquote
    filename = request.args.get('file', '')
    if not filename:
        return jsonify({'error': '缺少文件名'}), 400
    
    pages_dir = os.path.join(os.path.dirname(__file__), 'output', 'pages')
    file_path = os.path.join(pages_dir, filename)
    decoded_path = unquote(file_path)
    
    logger.info(f"读取页面: {decoded_path}")
    
    if not os.path.exists(decoded_path):
        return jsonify({'error': '文件不存在', 'path': decoded_path}), 404
    
    try:
        with open(decoded_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'success': True, 'content': content})
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'ok'})


@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取所有项目"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        projects = ProjectService.get_all_projects(limit=limit, offset=offset)
        for p in projects:
            if p.get('created_at'):
                p['created_at'] = p['created_at'].isoformat() if hasattr(p['created_at'], 'isoformat') else str(p['created_at'])
            if p.get('updated_at'):
                p['updated_at'] = p['updated_at'].isoformat() if hasattr(p['updated_at'], 'isoformat') else str(p['updated_at'])
        return jsonify({
            'success': True,
            'projects': projects,
            'count': len(projects)
        })
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """获取单个项目"""
    try:
        project = ProjectService.get_project(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404
        if project.get('created_at'):
            project['created_at'] = project['created_at'].isoformat() if hasattr(project['created_at'], 'isoformat') else str(project['created_at'])
        if project.get('updated_at'):
            project['updated_at'] = project['updated_at'].isoformat() if hasattr(project['updated_at'], 'isoformat') else str(project['updated_at'])
        return jsonify({
            'success': True,
            'project': project
        })
    except Exception as e:
        logger.error(f"获取项目失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects', methods=['POST'])
def create_project():
    """创建项目"""
    try:
        data = request.get_json()
        name = data.get('name', '未命名项目')
        description = data.get('description', '')
        project_type = data.get('type', 'business')
        icon = data.get('icon', '📊')

        project_id = ProjectService.create_project(
            name=name,
            description=description,
            type=project_type,
            icon=icon
        )

        return jsonify({
            'success': True,
            'project_id': project_id,
            'message': '项目创建成功'
        }), 201

    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目"""
    try:
        data = request.get_json()
        updates = {k: v for k, v in data.items() if k in [
            'name', 'description', 'type', 'icon', 'page_count'
        ]}

        if not updates:
            return jsonify({'error': '没有有效的更新字段'}), 400

        success = ProjectService.update_project(project_id, **updates)
        if not success:
            return jsonify({'error': '项目不存在'}), 404

        return jsonify({
            'success': True,
            'message': '项目更新成功'
        })

    except Exception as e:
        logger.error(f"更新项目失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    try:
        success = ProjectService.delete_project(project_id)
        if not success:
            return jsonify({'error': '项目不存在'}), 404

        return jsonify({
            'success': True,
            'message': '项目删除成功'
        })

    except Exception as e:
        logger.error(f"删除项目失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/search', methods=['GET'])
def search_projects():
    """搜索项目"""
    try:
        keyword = request.args.get('q', '')
        if not keyword:
            return jsonify({'success': True, 'projects': [], 'count': 0})

        projects = ProjectService.search_projects(keyword)
        return jsonify({
            'success': True,
            'projects': projects,
            'count': len(projects)
        })

    except Exception as e:
        logger.error(f"搜索项目失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/outlines', methods=['GET'])
def get_project_outlines(project_id):
    """获取项目的所有大纲"""
    try:
        outlines = OutlineService.get_outlines_by_project(project_id)
        return jsonify({
            'success': True,
            'outlines': outlines,
            'count': len(outlines)
        })
    except Exception as e:
        logger.error(f"获取大纲失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/outlines', methods=['POST'])
def create_outline():
    """创建大纲"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        title = data.get('title', '未命名大纲')
        page_count = data.get('page_count', 0)
        outline_data = data.get('outline_data')

        if not project_id:
            return jsonify({'error': '项目ID不能为空'}), 400

        outline_id = OutlineService.create_outline(
            project_id=project_id,
            title=title,
            outline_data=outline_data
        )

        ProjectService.update_project(project_id, page_count=page_count)

        return jsonify({
            'success': True,
            'outline_id': outline_id,
            'message': '大纲创建成功'
        }), 201

    except Exception as e:
        logger.error(f"创建大纲失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/outlines/<int:outline_id>', methods=['GET'])
def get_outline(outline_id):
    """获取大纲"""
    try:
        outline = OutlineService.get_outline(outline_id)
        if not outline:
            return jsonify({'error': '大纲不存在'}), 404
        return jsonify({
            'success': True,
            'outline': outline
        })
    except Exception as e:
        logger.error(f"获取大纲失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/outlines/<int:outline_id>', methods=['PUT'])
def update_outline(outline_id):
    """更新大纲"""
    try:
        data = request.get_json()
        updates = {k: v for k, v in data.items() if k in [
            'title', 'page_count', 'outline_data'
        ]}

        if not updates:
            return jsonify({'error': '没有有效的更新字段'}), 400

        success = OutlineService.update_outline(outline_id, **updates)
        if not success:
            return jsonify({'error': '大纲不存在'}), 404

        return jsonify({
            'success': True,
            'message': '大纲更新成功'
        })

    except Exception as e:
        logger.error(f"更新大纲失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ppts', methods=['POST'])
def create_ppt():
    """保存生成的PPT"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        outline_id = data.get('outline_id')
        style = data.get('style', 'modern')
        title = data.get('title', '')
        html_content = data.get('html_content', '')
        slide_count = data.get('slide_count', 0)
        status = data.get('status', 'completed')

        if not project_id:
            return jsonify({'error': '项目ID不能为空'}), 400

        ppt_id = GeneratedPptService.create_ppt(
            project_id=project_id,
            outline_id=outline_id,
            style=style,
            title=title,
            html_content=html_content,
            slide_count=slide_count,
            status=status
        )

        return jsonify({
            'success': True,
            'ppt_id': ppt_id,
            'message': 'PPT保存成功'
        }), 201

    except Exception as e:
        logger.error(f"保存PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/ppts', methods=['GET'])
def get_project_ppts(project_id):
    """获取项目的所有PPT"""
    try:
        limit = request.args.get('limit', 10, type=int)
        ppts = GeneratedPptService.get_ppts_by_project(project_id, limit=limit)
        return jsonify({
            'success': True,
            'ppts': ppts,
            'count': len(ppts)
        })
    except Exception as e:
        logger.error(f"获取PPT列表失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ppts/<int:ppt_id>', methods=['GET'])
def get_ppt(ppt_id):
    """获取PPT"""
    try:
        ppt = GeneratedPptService.get_ppt(ppt_id)
        if not ppt:
            return jsonify({'error': 'PPT不存在'}), 404
        return jsonify({
            'success': True,
            'ppt': ppt
        })
    except Exception as e:
        logger.error(f"获取PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/db-test', methods=['GET'])
def db_test():
    """数据库连接测试"""
    from database import test_connection
    result = test_connection()
    return jsonify(result)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    try:
        total_slides = GeneratedPptService.get_total_slides()
        project_count = len(ProjectService.get_all_projects(limit=1000))
        return jsonify({
            'success': True,
            'total_slides': total_slides,
            'project_count': project_count
        })
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates', methods=['GET'])
def get_templates():
    """获取模板列表"""
    try:
        import os
        templates_dir = os.path.join(os.path.dirname(__file__), 'templates', 'data')
        templates = []
        seen_template_ids = set()

        def load_template_summaries(directory, default_type):
            if not os.path.exists(directory):
                return
            for filename in os.listdir(directory):
                if filename.endswith('.json'):
                    filepath = os.path.join(directory, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                            template_id = template_data.get('template_id') or os.path.splitext(filename)[0]
                            if template_id in seen_template_ids:
                                continue
                            seen_template_ids.add(template_id)
                            templates.append({
                                'template_id': template_id,
                                'template_name': template_data.get('template_name'),
                                'description': template_data.get('description'),
                                'css_variables': template_data.get('css_variables'),
                                'tags': template_data.get('tags', []),
                                'is_default': template_data.get('is_default', False),
                                'page_types': list(template_data.get('page_types', {}).keys()),
                                'template_type': template_data.get('template_type', default_type)
                            })
                    except Exception as e:
                        logger.error(f"加载模板文件 {filepath} 失败: {e}")

        load_template_summaries(templates_dir, 'preset')
        load_template_summaries(os.path.join(templates_dir, 'user_generated'), 'user')

        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates', methods=['POST'])
def create_template():
    """创建新模板 - 保存用户生成的模板"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        template_data = data.get('template_data') or data

        template_id = template_data.get('template_id')
        if not template_id:
            return jsonify({'error': 'template_id 不能为空'}), 400

        logger.info(f"创建模板: {template_id}")

        output_dir = os.path.join(
            os.path.dirname(__file__), 'templates', 'data', 'user_generated'
        )
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{template_id}.json")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, ensure_ascii=False, indent=2)

        logger.info(f"模板已保存: {output_path}")

        # 刷新模板加载器缓存，使新模板立即可用
        from templates.template_loader import get_loader
        get_loader().reload()
        logger.info("模板加载器已刷新")

        return jsonify({
            'success': True,
            'message': '模板保存成功',
            'template': {
                'template_id': template_id,
                'template_name': template_data.get('template_name', ''),
                'description': template_data.get('description', ''),
                'css_variables': template_data.get('css_variables'),
                'tags': template_data.get('tags', []),
                'page_types': list(template_data.get('page_types', {}).keys()),
                'template_type': template_data.get('template_type', 'user'),
                'is_default': False
            }
        }), 201

    except Exception as e:
        logger.error(f"创建模板失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates/<template_id>', methods=['PUT'])
def update_template(template_id):
    """更新模板的名称、描述、标签"""
    try:
        data = request.get_json() or {}
        output_dir = os.path.join(os.path.dirname(__file__), 'templates', 'data', 'user_generated')
        filepath = os.path.join(output_dir, f"{template_id}.json")
        if not os.path.exists(filepath):
            return jsonify({'error': '模板不存在'}), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            tpl = json.load(f)

        if 'template_name' in data:
            tpl['template_name'] = data['template_name']
        if 'description' in data:
            tpl['description'] = data['description']
        if 'tags' in data:
            tpl['tags'] = data['tags']

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tpl, f, ensure_ascii=False, indent=2)

        from templates.template_loader import get_loader
        get_loader().reload()

        return jsonify({
            'success': True,
            'template': {
                'template_id': template_id,
                'template_name': tpl.get('template_name', ''),
                'description': tpl.get('description', ''),
                'tags': tpl.get('tags', []),
            }
        })
    except Exception as e:
        logger.error(f"更新模板失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/templates/<template_id>', methods=['DELETE'])
def remove_template(template_id):
    """删除用户模板"""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), 'templates', 'data', 'user_generated')
        filepath = os.path.join(output_dir, f"{template_id}.json")
        if not os.path.exists(filepath):
            return jsonify({'error': '模板不存在'}), 404

        os.remove(filepath)

        from templates.template_loader import get_loader
        get_loader().reload()

        return jsonify({'success': True, 'message': '模板已删除'})
    except Exception as e:
        logger.error(f"删除模板失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/save-preview-html', methods=['POST'])
def save_preview_html():
    """保存 / 清空模板预览 HTML 到固定路径"""
    try:
        data = request.get_json() or {}
        template_id = (data.get('template_id') or 'unknown').strip()
        html = data.get('html') or ''
        # 安全过滤：只允许字母数字下划线横线
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', template_id) or 'unknown'
        out_dir = os.path.join(os.path.dirname(__file__), 'test', 'output', 'preview_gen')
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, f'preview_{safe_id}.html')
        if html:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            return jsonify({'success': True, 'path': filepath, 'size': len(html)})
        else:
            # html 为空时删除旧预览文件
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'success': True, 'cleared': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 注册模板生成 API（模块级，确保任何启动方式都生效）
register_template_api_routes(app)

def main():
    """主函数"""
    logger.info(f"启动LandPPT Demo服务: http://{APP_HOST}:{APP_PORT}")
    app.run(host=APP_HOST, port=APP_PORT, debug=DEBUG)


if __name__ == '__main__':
    main()
