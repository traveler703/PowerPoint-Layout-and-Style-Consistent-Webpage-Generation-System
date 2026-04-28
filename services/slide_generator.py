# 此文件已废弃

"""
幻灯片生成服务 - LandPPT原版核心
步骤7: 生成单页HTML (整合所有策略)
"""
import logging
from typing import Dict, Any, List, Optional
from core.deepseek_client import DeepSeekClient
from core.canvas_strategy import CanvasStrategy
from core.layout_library import LayoutLibrary
from core.style_genes import StyleGeneExtractor
from core.global_constitution import GlobalConstitutionGenerator
from services.html_cleanup import HtmlCleanupService
from services.html_validator import HtmlValidatorService
from prompts.design_prompts import DESIGN_PROMPT

logger = logging.getLogger(__name__)


class SlideGenerator:
    """
    幻灯片生成器 - 整合所有策略
    步骤7: 生成单页HTML
    """
    
    def __init__(
        self,
        client: DeepSeekClient = None,
        template_html: str = None
    ):
        self.client = client or DeepSeekClient()
        self.template_html = template_html or self._get_default_template()
        self.html_cleanup = HtmlCleanupService()
        self.html_validator = HtmlValidatorService()
        self.canvas_strategy = CanvasStrategy()
        self.layout_library = LayoutLibrary()
        self.style_gene_extractor = StyleGeneExtractor(self.client)
        self.constitution_generator = GlobalConstitutionGenerator(self.client)
        
        # 缓存设计基因和全局宪法
        self._style_genes = None
        self._global_constitution = None
    
    def _get_default_template(self) -> str:
        """获取默认模板HTML"""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
    </style>
</head>
<body></body>
</html>"""
    
    async def initialize(self, topic: str, scenario: str, style: str, slides: List[Dict]) -> None:
        """
        初始化：提取设计基因和生成全局宪法
        
        Args:
            topic: 主题
            scenario: 场景
            style: 风格
            slides: 所有幻灯片大纲
        """
        logger.info("开始初始化设计基因和全局宪法...")
        
        # 提取设计基因
        self._style_genes = await self.style_gene_extractor.extract_style_genes(self.template_html)
        logger.info("设计基因提取完成")
        
        # 生成全局宪法
        self._global_constitution = await self.constitution_generator.generate_constitution(
            topic=topic,
            scenario=scenario,
            style=style,
            all_slides=slides,
            style_genes=self._style_genes
        )
        logger.info("全局宪法生成完成")
    
    async def generate_slide(
        self,
        slide_data: Dict[str, Any],
        page_number: int,
        total_pages: int
    ) -> str:
        """
        生成单页HTML
        
        Args:
            slide_data: 幻灯片数据
            page_number: 当前页码
            total_pages: 总页数
            
        Returns:
            HTML字符串
        """
        logger.info(f"生成第{page_number}页: {slide_data.get('title', '')}")
        
        try:
            # 构建生成提示词
            prompt = self._build_design_prompt(slide_data, page_number, total_pages)
            
            system_prompt = """你是一位专业的PPT设计师。
请根据提供的信息生成高质量的单页HTML。
必须严格遵守画布约束和设计基因。"""
            
            # 调用API生成
            response = self.client.chat(system_prompt, prompt, temperature=0.7)
            
            # 步骤8: HTML清理
            html = self.html_cleanup.cleanup_html_response(response)
            
            # 验证HTML长度
            if not self.html_cleanup.validate_html_length(html):
                logger.warning(f"第{page_number}页HTML长度不足，使用备用方案")
                html = self._generate_fallback_html(slide_data, page_number, total_pages)
            
            # 步骤9: HTML验证与修复
            html, validation_result = self.html_validator.validate_and_fix(html)
            
            if not validation_result['is_valid']:
                logger.warning(f"第{page_number}页HTML验证失败: {validation_result['errors']}")
            
            # 确保包含画布约束
            html = self._ensure_canvas_constraints(html)
            
            logger.info(f"第{page_number}页生成完成")
            return html
            
        except Exception as e:
            logger.error(f"生成第{page_number}页失败: {e}")
            return self._generate_fallback_html(slide_data, page_number, total_pages)
    
    def _build_design_prompt(
        self,
        slide_data: Dict[str, Any],
        page_number: int,
        total_pages: int
    ) -> str:
        """构建设计提示词"""
        slide_type = slide_data.get('slide_type', 'content')
        title = slide_data.get('title', '')
        content_points = slide_data.get('content_points', [])
        
        # 格式化内容要点
        content_str = "\n".join([f"- {point}" for point in content_points])
        
        return DESIGN_PROMPT.format(
            page_number=page_number,
            total_pages=total_pages,
            slide_type=slide_type,
            title=title,
            content_points=content_str,
            style_genes=self._style_genes or "使用现代简约风格",
            global_constitution=self._global_constitution or "保持内容丰富，排版整洁",
            layout_methods=self.layout_library.get_layout_methods()
        )
    
    def _ensure_canvas_constraints(self, html: str) -> str:
        """确保HTML包含画布约束"""
        canvas_width = 1280
        canvas_height = 720
        
        # 检查是否已经有canvas约束
        if 'width: 1280px' not in html and 'width:1280px' not in html:
            # 添加画布样式
            if '<style' in html.lower():
                # 追加到现有style
                html = html.replace(
                    '</style>',
                    f'''
        .slide-canvas {{
            width: {canvas_width}px !important;
            height: {canvas_height}px !important;
            max-width: {canvas_width}px !important;
            max-height: {canvas_height}px !important;
            overflow: hidden !important;
            position: relative !important;
        }}
        body, html {{
            margin: 0 !important;
            padding: 0 !important;
            width: {canvas_width}px !important;
            height: {canvas_height}px !important;
            overflow: hidden !important;
        }}
                    </style>''',
                    1
                )
            else:
                # 添加新的style标签
                html = f'''
<style>
    .slide-canvas {{
        width: {canvas_width}px !important;
        height: {canvas_height}px !important;
        max-width: {canvas_width}px !important;
        max-height: {canvas_height}px !important;
        overflow: hidden !important;
        position: relative !important;
    }}
    body, html {{
        margin: 0 !important;
        padding: 0 !important;
        width: {canvas_width}px !important;
        height: {canvas_height}px !important;
        overflow: hidden !important;
    }}
</style>
{html}'''
        
        return html
    
    def _generate_fallback_html(
        self,
        slide_data: Dict[str, Any],
        page_number: int,
        total_pages: int
    ) -> str:
        """生成备用HTML（当API调用失败时）"""
        slide_type = slide_data.get('slide_type', 'content')
        title = slide_data.get('title', '')
        content_points = slide_data.get('content_points', [])
        content_html = "<br>".join([f"• {point}" for point in content_points])
        
        if slide_type == 'title':
            return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body, html {{ margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden; font-family: "Microsoft YaHei", sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .container {{ display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; color: white; text-align: center; }}
        h1 {{ font-size: 56px; font-weight: bold; margin-bottom: 20px; }}
        p {{ font-size: 24px; opacity: 0.9; }}
        .page-number {{ position: absolute; bottom: 20px; right: 40px; font-size: 14px; opacity: 0.7; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>第 {page_number} / {total_pages} 页</p>
    </div>
    <div class="page-number">{page_number} / {total_pages}</div>
</body>
</html>'''
        else:
            return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body, html {{ margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden; font-family: "Microsoft YaHei", sans-serif; background: #ffffff; }}
        .header {{ height: 80px; padding: 20px 60px; background: linear-gradient(90deg, #667eea, #764ba2); color: white; display: flex; align-items: center; }}
        .header h2 {{ font-size: 28px; font-weight: bold; }}
        .content {{ padding: 40px 60px; font-size: 20px; line-height: 1.8; color: #333; }}
        .footer {{ position: absolute; bottom: 0; left: 0; right: 0; height: 60px; padding: 20px 60px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #eee; font-size: 14px; color: #666; }}
    </style>
</head>
<body>
    <div class="header"><h2>{title}</h2></div>
    <div class="content">{content_html}</div>
    <div class="footer">
        <span>第 {page_number} / {total_pages} 页</span>
    </div>
</body>
</html>'''
    
    async def generate_all_slides(
        self,
        slides: List[Dict[str, Any]],
        topic: str = "",
        scenario: str = "general",
        style: str = "modern"
    ) -> List[Dict[str, Any]]:
        """
        生成所有幻灯片
        
        Args:
            slides: 幻灯片大纲列表
            topic: 主题
            scenario: 场景
            style: 风格
            
        Returns:
            生成结果列表
        """
        # 初始化设计基因和全局宪法
        await self.initialize(topic, scenario, style, slides)
        
        total_pages = len(slides)
        results = []
        
        for i, slide in enumerate(slides):
            page_number = i + 1
            html = await self.generate_slide(slide, page_number, total_pages)
            
            results.append({
                'page_number': page_number,
                'title': slide.get('title', ''),
                'slide_type': slide.get('slide_type', 'content'),
                'html': html
            })
        
        return results
