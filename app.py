"""
LandPPT Demo - Flask应用
主入口文件
"""
import asyncio
import json
import logging
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from config import APP_HOST, APP_PORT, DEBUG
from services.project_service import (
    ProjectService, OutlineService, GeneratedPptService
)
from engine.content import parse_user_document
from pipeline import run_pipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'landppt-demo-secret-key'
CORS(app)

# /api/parse-text 中发给LLM的最大字符数（不是用户上传上限）
MAX_LLM_INPUT_CHARS = 20000


def _prepare_text_for_llm(text: str, max_chars: int = MAX_LLM_INPUT_CHARS) -> str:
    """压缩超长文本，避免触发模型上下文长度限制。"""
    if len(text) <= max_chars:
        return text

    # 保留头尾关键上下文，并插入明显的省略标记
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
    return render_template('index.html')


@app.route('/api/parse-text', methods=['POST'])
def parse_text():
    """解析文本内容API - 使用 pipeline 语义解析。"""
    try:
        data = request.get_json()
        
        text = data.get('text', '')
        project_id = data.get('project_id')
        
        if not text or len(text.strip()) < 10:
            return jsonify({'error': '文本内容太少，至少需要10个字符'}), 400
        
        original_len = len(text)
        llm_text = _prepare_text_for_llm(text)
        logger.info(
            f"解析文本: 原始长度={original_len}字符, 输入长度={len(llm_text)}字符, project_id={project_id}"
        )
        parse_result = _semantic_to_parse_result(llm_text)
        
        logger.info(f"解析完成: title={parse_result.get('title', 'N/A')}, sections={len(parse_result.get('sections', []))}")

        # 返回解析结果（不自动保存，需要用户点击"开始应用"）
        return jsonify({
            'success': True,
            'result': parse_result,
            'meta': {
                'original_text_length': original_len,
                'llm_input_length': len(llm_text),
                'input_truncated': original_len > len(llm_text)
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

        # 存储原始文本（用于刷新时重新解析）
        original_text = data.get('original_text', '')

        # 保存到 project 表的额外字段
        ProjectService.update_project(project_id,
            parse_title=parse_result.get('title', '未命名文档'),
            parse_summary=parse_result.get('summary', ''),
            parse_sections=json.dumps(parse_result.get('sections', []), ensure_ascii=False),
            parse_original_text=original_text,
            page_count=len(parse_result.get('sections', [])) + 1  # +1 封面页
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

        # 解析sections JSON
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
    """生成大纲API（基于 pipeline 语义解析构建）。"""
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


@app.route('/api/generate-ppt-from-outline', methods=['POST'])
def generate_ppt_from_outline():
    """使用已有大纲生成PPT（走 pipeline 流程）"""
    try:
        data = request.get_json()
        
        outline = data.get('outline', {})
        topic = data.get('topic', '')
        if not outline or 'slides' not in outline:
            return jsonify({'error': '大纲数据无效'}), 400
        
        slides = outline.get('slides', [])
        if not slides:
            return jsonify({'error': '大纲中没有幻灯片'}), 400
        
        logger.info(f"从大纲生成PPT(pipeline): topic={topic}, slides={len(slides)}")
        pipeline_input = _outline_to_pipeline_input(outline, fallback_title=topic or "演示文稿")
        ppt_html, report = asyncio.run(run_pipeline(pipeline_input, output_format="html"))
        
        return jsonify({
            'success': True,
            'html': ppt_html,
            'slide_count': len(slides),
            'outline': outline,
            'evaluation': report.model_dump()
        })
        
    except Exception as e:
        logger.error(f"从大纲生成PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-ppt', methods=['POST'])
def generate_ppt():
    """生成PPT API（统一走 pipeline 流程）"""
    try:
        data = request.get_json()
        
        mode = data.get('mode', 'auto')  # 'auto' 或 'manual'
        
        if mode == 'manual':
            # 手动输入模式
            title = data.get('title', '')
            outline_text = data.get('outline_text', '')
            
            if not title:
                return jsonify({'error': 'PPT标题不能为空'}), 400
            
            if not outline_text:
                return jsonify({'error': '大纲内容不能为空'}), 400
            
            parse_result = _semantic_to_parse_result(outline_text)
            parse_result['title'] = title
            outline = _build_outline_from_parse_result(parse_result)
            topic = title
            
        else:
            # AI生成模式
            topic = data.get('topic', '')
            
            if not topic:
                return jsonify({'error': '主题不能为空'}), 400
            
            source_text = data.get('document_text') or topic
            parse_result = _semantic_to_parse_result(source_text)
            if not parse_result.get('title'):
                parse_result['title'] = topic
            outline = _build_outline_from_parse_result(parse_result)
        
        slides = outline.get('slides', [])
        if not slides:
            return jsonify({'error': '大纲中没有幻灯片'}), 400
        
        logger.info(f"生成PPT(pipeline): topic={topic}, slides={len(slides)}")
        pipeline_input = _outline_to_pipeline_input(outline, fallback_title=topic or "演示文稿")
        ppt_html, report = asyncio.run(run_pipeline(pipeline_input, output_format="html"))
        
        return jsonify({
            'success': True,
            'html': ppt_html,
            'slide_count': len(slides),
            'outline': outline,
            'evaluation': report.model_dump()
        })
        
    except Exception as e:
        logger.error(f"生成PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-ppt-stream', methods=['POST'])
def generate_ppt_stream():
    """流式生成PPT - 基于 pipeline 按页推送给前端"""
    from flask import Response
    
    try:
        data = request.get_json()
        
        outline = data.get('outline', {})
        topic = data.get('topic', 'PPT演示文稿')
        if not outline or 'slides' not in outline:
            return jsonify({'error': '大纲数据无效'}), 400
        
        slides = outline.get('slides', [])
        if not slides:
            return jsonify({'error': '大纲中没有幻灯片'}), 400
        
        logger.info(f"流式生成PPT: topic={topic}, slides={len(slides)}")
        
        def generate():
            try:
                total_pages = len(slides)
                
                for i, slide_data in enumerate(slides):
                    page_number = i + 1
                    
                    try:
                        page_text = _slide_to_page_markdown(slide_data)
                        html, report = asyncio.run(run_pipeline(page_text, output_format="html"))
                        slide_info = {
                            'type': 'slide',
                            'page_number': page_number,
                            'title': slide_data.get('title', ''),
                            'html': html,
                            'evaluation': report.model_dump()
                        }
                        json_str = json.dumps(slide_info, ensure_ascii=False)
                        logger.info(f"[SSE] 准备发送第{page_number}页, html长度={len(html)}")
                        yield f"data: {json_str}\n\n"
                        logger.info(f"[SSE] 已发送第{page_number}页")
                        
                    except Exception as e:
                        logger.error(f"生成第{page_number}页失败: {e}")
                        error_info = {
                            'type': 'error',
                            'page_number': page_number,
                            'message': str(e)
                        }
                        yield f"data: {json.dumps(error_info, ensure_ascii=False)}\n\n"
                
                # 发送完成信号
                complete_info = {'type': 'complete'}
                yield f"data: {json.dumps(complete_info, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                error_info = {'type': 'error', 'message': str(e)}
                yield f"data: {json.dumps(error_info, ensure_ascii=False)}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        logger.error(f"流式生成PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-preview', methods=['POST'])
def generate_preview():
    """生成单页预览（走 pipeline 流程）"""
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
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    return send_file(os.path.join(output_dir, filename))


@app.route('/api/upload-document', methods=['POST'])
def upload_document():
    """
    文件上传解析 API。
    支持 Markdown/TXT、PDF、DOCX、PPTX 四种格式。
    返回统一的 DocumentParseResult JSON 结构。
    """
    import os
    import tempfile
    from parsers.base import BaseDocumentParser, SourceFormat
    from parsers.markdown_parser import MarkdownParser
    from parsers.pdf_parser import PdfParser
    from parsers.docx_parser import DocxParser
    from parsers.pptx_parser import PptxParser

    try:
        if 'file' not in request.files:
            return jsonify({'error': '请上传文件（字段名: file）'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        filename = file.filename
        fmt = BaseDocumentParser.detect_format(filename)
        file_bytes = file.read()

        if len(file_bytes) == 0:
            return jsonify({'error': '文件内容为空'}), 400

        # 文件大小限制: 20MB
        if len(file_bytes) > 20 * 1024 * 1024:
            return jsonify({'error': '文件大小超过 20MB 限制'}), 400

        logger.info(f"上传文档: filename={filename}, format={fmt.value}, size={len(file_bytes)} bytes")

        # 根据格式选择解析器
        parser_map = {
            SourceFormat.MARKDOWN: MarkdownParser,
            SourceFormat.TXT: MarkdownParser,
            SourceFormat.PDF: PdfParser,
            SourceFormat.DOCX: DocxParser,
            SourceFormat.PPTX: PptxParser,
        }

        parser_cls = parser_map.get(fmt)
        if not parser_cls:
            return jsonify({'error': f'不支持的文件格式: {filename}'}), 400

        parser = parser_cls()

        # 对 Markdown/TXT 传文本，其他格式传字节
        if fmt in (SourceFormat.MARKDOWN, SourceFormat.TXT):
            source = file_bytes.decode('utf-8', errors='replace')
        else:
            source = file_bytes

        result = parser.parse(source, filename=filename)

        logger.info(
            f"文档解析完成: title={result.metadata.title}, "
            f"pages={result.metadata.page_count}, chars={result.metadata.total_chars}"
        )

        return jsonify({
            'success': True,
            'result': result.model_dump(exclude_none=True),
            'meta': {
                'filename': filename,
                'format': fmt.value,
                'file_size': len(file_bytes),
                'page_count': result.metadata.page_count,
                'total_chars': result.metadata.total_chars,
            }
        })

    except ImportError as e:
        logger.error(f"缺少解析依赖: {e}")
        return jsonify({'error': f'服务器缺少依赖库: {e}'}), 500
    except Exception as e:
        logger.error(f"文档解析失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'文档解析失败: {str(e)}'}), 500


@app.route('/api/supported-formats', methods=['GET'])
def get_supported_formats():
    """获取支持的文件格式列表"""
    return jsonify({
        'success': True,
        'formats': [
            {'extension': '.md', 'name': 'Markdown', 'mime': 'text/markdown'},
            {'extension': '.txt', 'name': '纯文本', 'mime': 'text/plain'},
            {'extension': '.pdf', 'name': 'PDF', 'mime': 'application/pdf'},
            {'extension': '.docx', 'name': 'Word', 'mime': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
            {'extension': '.pptx', 'name': 'PowerPoint', 'mime': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'},
        ],
        'max_file_size_mb': 20
    })


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'ok'})


# ============================================
# 数据库CRUD API接口
# ============================================

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取所有项目"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        projects = ProjectService.get_all_projects(limit=limit, offset=offset)
        # 转换时间字段为ISO格式
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
        # 转换时间字段为ISO格式
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
        scenario = data.get('scenario', 'general')
        audience = data.get('audience', '通用受众')
        page_count = data.get('page_count', 0)
        outline_data = data.get('outline_data')

        if not project_id:
            return jsonify({'error': '项目ID不能为空'}), 400

        outline_id = OutlineService.create_outline(
            project_id=project_id,
            title=title,
            scenario=scenario,
            audience=audience,
            page_count=page_count,
            outline_data=outline_data
        )

        # 更新项目页数
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
            'title', 'scenario', 'audience', 'page_count', 'outline_data'
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


def main():
    """主函数"""
    logger.info(f"启动LandPPT Demo服务: http://{APP_HOST}:{APP_PORT}")
    app.run(host=APP_HOST, port=APP_PORT, debug=DEBUG)


if __name__ == '__main__':
    main()
