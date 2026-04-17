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
from services.outline_generator import OutlineGenerator
from services.slide_generator import SlideGenerator
from services.ppt_combiner import PptCombiner
from services.project_service import (
    ProjectService, OutlineService, SlideService, GeneratedPptService
)
from services.text_parser import TextParser

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

# 全局客户端
outline_generator = OutlineGenerator()
slide_generator = SlideGenerator()
text_parser = TextParser()


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/parse-text', methods=['POST'])
def parse_text():
    """解析文本内容API - 使用LLM生成PPT大纲"""
    try:
        data = request.get_json()
        
        text = data.get('text', '')
        project_id = data.get('project_id')
        
        if not text or len(text.strip()) < 10:
            return jsonify({'error': '文本内容太少，至少需要10个字符'}), 400
        
        logger.info(f"解析文本: 长度={len(text)}字符, project_id={project_id}")
        
        # 构建LLM提示词 - 根据用户文本生成PPT大纲
        prompt = f"""请分析以下文本内容，生成一个结构清晰的PPT大纲。

**用户输入内容**：
{text}

**输出格式要求**：
必须返回纯JSON格式，包含以下字段：
{{
    "title": "PPT标题（从内容中提取或概括）",
    "subtitle": "副标题（可选）",
    "summary": "内容摘要（50字以内）",
    "slides": [
        {{
            "page_number": 1,
            "title": "页面标题",
            "content_points": ["要点1", "要点2", "要点3"],
            "slide_type": "title"
        }},
        {{
            "page_number": 2,
            "title": "页面标题",
            "content_points": ["要点1", "要点2"],
            "slide_type": "content"
        }}
    ]
}}

**幻灯片类型说明**：
- title: 封面页（必须第1页）
- agenda: 目录页（可选）
- content: 内容页（主体）
- section_header: 章节分隔页（可选）
- conclusion: 结论总结页（可选）
- thankyou: 感谢页（最后一页可选）

**生成规则**：
1. 根据文本内容合理规划页数（建议5-10页）
2. 第1页必须是封面页 (title)
3. 内容页要提取文本中的关键信息和要点
4. 保持逻辑清晰，层次分明
5. 每页要点控制在2-4个

请直接返回JSON格式，不要包含任何解释文字。"""

        system_prompt = """你是一位专业的PPT大纲策划专家。
请根据用户提供的文本内容，生成结构清晰、内容专业的PPT大纲。
必须返回有效的JSON格式，不要包含任何解释文字。"""
        
        # 调用LLM生成大纲
        result = outline_generator.client.chat(system_prompt, prompt, temperature=0.7)
        
        # 解析JSON响应
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', result, re.IGNORECASE)
        if json_match:
            outline = json.loads(json_match.group(1))
        else:
            json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', result)
            if json_match:
                outline = json.loads(json_match.group(1))
            else:
                outline = json.loads(result)
        
        # 转换为前端需要的格式
        parse_result = {
            'title': outline.get('title', '未命名文档'),
            'summary': outline.get('summary', ''),
            'sections': []
        }
        
        # 转换slides为sections
        slides = outline.get('slides', [])
        for slide in slides:
            parse_result['sections'].append({
                'title': slide.get('title', ''),
                'content': '',
                'bullets': slide.get('content_points', [])
            })
        
        logger.info(f"解析完成: title={parse_result.get('title', 'N/A')}, sections={len(parse_result.get('sections', []))}")

        # 返回解析结果（不自动保存，需要用户点击"开始应用"）
        return jsonify({
            'success': True,
            'result': parse_result
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
    """生成大纲API"""
    try:
        data = request.get_json()
        
        topic = data.get('topic', '')
        scenario = data.get('scenario', 'general')
        audience = data.get('audience', '通用受众')
        page_count = data.get('page_count', 10)
        
        if not topic:
            return jsonify({'error': '主题不能为空'}), 400
        
        logger.info(f"生成大纲: topic={topic[:50]}..., page_count={page_count}")
        
        # 生成大纲
        outline = asyncio.run(
            outline_generator.generate_outline(
                topic=topic,
                scenario=scenario,
                audience=audience,
                page_count=page_count
            )
        )
        
        return jsonify({
            'success': True,
            'outline': outline
        })
        
    except Exception as e:
        logger.error(f"生成大纲失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-ppt-from-outline', methods=['POST'])
def generate_ppt_from_outline():
    """使用已有大纲生成PPT"""
    try:
        data = request.get_json()
        
        outline = data.get('outline', {})
        topic = data.get('topic', '')
        scenario = data.get('scenario', 'general')
        style = data.get('style', 'modern')
        
        if not outline or 'slides' not in outline:
            return jsonify({'error': '大纲数据无效'}), 400
        
        slides = outline_generator.extract_slides_for_generation(outline)
        
        if not slides:
            return jsonify({'error': '大纲中没有幻灯片'}), 400
        
        logger.info(f"从大纲生成PPT: topic={topic}, slides={len(slides)}")
        
        # 生成所有幻灯片
        slide_results = asyncio.run(
            slide_generator.generate_all_slides(
                slides=slides,
                topic=topic,
                scenario=scenario,
                style=style
            )
        )
        
        # 组合为完整HTML
        ppt_html = PptCombiner.combine_slides_to_html(
            slides=slide_results,
            title=topic
        )
        
        return jsonify({
            'success': True,
            'html': ppt_html,
            'slide_count': len(slide_results),
            'outline': outline
        })
        
    except Exception as e:
        logger.error(f"从大纲生成PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-ppt', methods=['POST'])
def generate_ppt():
    """生成PPT API"""
    try:
        data = request.get_json()
        
        mode = data.get('mode', 'auto')  # 'auto' 或 'manual'
        style = data.get('style', 'modern')
        
        if mode == 'manual':
            # 手动输入模式
            title = data.get('title', '')
            outline_text = data.get('outline_text', '')
            
            if not title:
                return jsonify({'error': 'PPT标题不能为空'}), 400
            
            if not outline_text:
                return jsonify({'error': '大纲内容不能为空'}), 400
            
            # 解析手动输入的大纲
            outline = outline_generator.parse_manual_outline(title, outline_text)
            topic = title
            
        else:
            # AI生成模式
            topic = data.get('topic', '')
            outline = data.get('outline', {})
            scenario = data.get('scenario', 'general')
            
            if not topic:
                return jsonify({'error': '主题不能为空'}), 400
            
            # 生成大纲
            page_count = data.get('page_count', 10)
            outline = asyncio.run(
                outline_generator.generate_outline(
                    topic=topic,
                    scenario=scenario,
                    audience=data.get('audience', '通用受众'),
                    page_count=page_count
                )
            )
        
        # 提取幻灯片
        slides = outline_generator.extract_slides_for_generation(outline)
        
        if not slides:
            return jsonify({'error': '大纲中没有幻灯片'}), 400
        
        logger.info(f"生成PPT: topic={topic}, slides={len(slides)}")
        
        # 生成所有幻灯片
        slide_results = asyncio.run(
            slide_generator.generate_all_slides(
                slides=slides,
                topic=topic,
                scenario=data.get('scenario', 'general'),
                style=style
            )
        )
        
        # 组合为完整HTML
        ppt_html = PptCombiner.combine_slides_to_html(
            slides=slide_results,
            title=topic
        )
        
        return jsonify({
            'success': True,
            'html': ppt_html,
            'slide_count': len(slide_results),
            'outline': outline
        })
        
    except Exception as e:
        logger.error(f"生成PPT失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-ppt-stream', methods=['POST'])
def generate_ppt_stream():
    """流式生成PPT - 每生成一页就推送给前端"""
    from flask import Response
    
    try:
        data = request.get_json()
        
        outline = data.get('outline', {})
        topic = data.get('topic', 'PPT演示文稿')
        scenario = data.get('scenario', 'general')
        style = data.get('style', 'modern')
        
        if not outline or 'slides' not in outline:
            return jsonify({'error': '大纲数据无效'}), 400
        
        slides = outline_generator.extract_slides_for_generation(outline)
        
        if not slides:
            return jsonify({'error': '大纲中没有幻灯片'}), 400
        
        logger.info(f"流式生成PPT: topic={topic}, slides={len(slides)}")
        
        def generate():
            try:
                # 初始化设计基因和全局宪法
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    slide_generator.initialize(topic, scenario, style, slides)
                )
                
                total_pages = len(slides)
                
                for i, slide_data in enumerate(slides):
                    page_number = i + 1
                    
                    try:
                        # 生成单页
                        html = loop.run_until_complete(
                            slide_generator.generate_slide(slide_data, page_number, total_pages)
                        )
                        
                        # 调试：保存HTML到文件
                        import os
                        output_dir = os.path.join(os.path.dirname(__file__), 'output')
                        os.makedirs(output_dir, exist_ok=True)
                        output_file = os.path.join(output_dir, f'slide_{page_number}.html')
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(html)
                        logger.info(f"已保存第{page_number}页HTML到: {output_file}")
                        
                        # 发送数据
                        import json
                        slide_info = {
                            'type': 'slide',
                            'page_number': page_number,
                            'title': slide_data.get('title', ''),
                            'html': html
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
                
                loop.close()
                
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
    """生成单页预览"""
    try:
        data = request.get_json()
        
        slide_data = data.get('slide_data', {})
        page_number = data.get('page_number', 1)
        total_pages = data.get('total_pages', 1)
        topic = data.get('topic', '')
        scenario = data.get('scenario', 'general')
        style = data.get('style', 'modern')
        
        if not slide_data:
            return jsonify({'error': '幻灯片数据不能为空'}), 400
        
        logger.info(f"生成预览: page={page_number}/{total_pages}")
        
        # 初始化设计基因和宪法
        slides = [slide_data]
        asyncio.run(
            slide_generator.initialize(topic, scenario, style, slides)
        )
        
        # 生成单页
        html = asyncio.run(
            slide_generator.generate_slide(slide_data, page_number, total_pages)
        )
        
        return jsonify({
            'success': True,
            'html': html
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
