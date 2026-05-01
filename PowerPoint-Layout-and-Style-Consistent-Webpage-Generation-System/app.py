"""
LandPPT Demo - Flask应用
主入口文件（Pipeline 引擎）
"""
import asyncio
import json
import logging
import os
import time
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from config import APP_HOST, APP_PORT, DEBUG
from services.project_service import (
    ProjectService, OutlineService, GeneratedPptService
)
from engine.content import parse_user_document
from engine.types import SemanticPageInput
from pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'landppt-demo-secret-key'
CORS(app)

MAX_LLM_INPUT_CHARS = 20000


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
        sections = []
        current_section = None

        for p in pages_data:
            page_type = p.get('page_type', 'content')
            if page_type == 'cover':
                title = p.get('title', title)
                subtitle = p.get('subtitle', '')
                date_badge = p.get('date_badge', '')
            elif page_type == 'section':
                current_section = {
                    'title': p.get('subtitle', p.get('title', '')),
                    'content_pages': []
                }
                sections.append(current_section)
            elif page_type == 'content':
                if not sections:
                    current_section = {'title': '默认章节', 'content_pages': []}
                    sections.append(current_section)
                sections[-1]['content_pages'].append({
                    'title': p.get('title', ''),
                    'summary': p.get('summary', ''),
                    'bullets': p.get('bullets', [])
                })

        if not sections:
            return jsonify({'error': '没有找到任何章节内容'}), 400

        # 构建 outline
        outline = {
            'title': title,
            'subtitle': subtitle,
            'date_badge': date_badge,
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

        # 读取生成的 HTML
        html_content = ""
        if result.success and result.output_path:
            with open(result.output_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        # 获取页面文件目录
        pages_dir = os.path.join(os.path.dirname(result.output_path), "pages") if result.output_path else ""
        
        # 构建 slides 数组 - 返回页面HTML内容
        slides = []
        for i, layout in enumerate(result.page_layouts):
            page_num = layout.get('page_number', i + 1)
            page_type = layout.get('type', 'content')
            title = layout.get('title', '')

            # 读取页面HTML内容
            page_html = ""
            page_file_path = None
            if os.path.exists(pages_dir):
                for fname in os.listdir(pages_dir):
                    if fname.startswith(f"{page_num:02d}_"):
                        page_file_path = f"/output/pages/{fname}"
                        page_file_full = os.path.join(pages_dir, fname)
                        with open(page_file_full, "r", encoding="utf-8") as pf:
                            page_html = pf.read()
                        break

            slides.append({
                'page_type': page_type,
                'title': title,
                'layout_type': layout.get('layout_type', ''),
                'page_number': page_num,
                'page_url': page_file_path,  # 页面文件路径
                'html': page_html,  # 页面HTML内容
            })

        logger.info(f"[Parallel] 生成完成: {result.page_count} 页, {result.document_size} chars")

        return jsonify({
            'success': result.success,
            'html': html_content,
            'slides': slides,
            'page_count': result.page_count,
            'document_size': result.document_size,
            'output_path': result.output_path,
            'error': result.error,
        })

    except Exception as e:
        logger.error(f"并行生成PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


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

        if os.path.exists(templates_dir):
            for filename in os.listdir(templates_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(templates_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                            # 只返回必要的字段
                            templates.append({
                                'template_id': template_data.get('template_id'),
                                'template_name': template_data.get('template_name'),
                                'description': template_data.get('description'),
                                'css_variables': template_data.get('css_variables'),
                                'tags': template_data.get('tags', []),
                                'is_default': template_data.get('is_default', False),
                                'page_types': list(template_data.get('page_types', {}).keys())
                            })
                    except Exception as e:
                        logger.error(f"加载模板文件 {filename} 失败: {e}")

        return jsonify({
            'success': True,
            'templates': templates
        })
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        return jsonify({'error': str(e)}), 500


def main():
    """主函数"""
    logger.info(f"启动LandPPT Demo服务: http://{APP_HOST}:{APP_PORT}")
    app.run(host=APP_HOST, port=APP_PORT, debug=DEBUG)


if __name__ == '__main__':
    main()
