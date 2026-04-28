"""
设计基因提取模块 - LandPPT原版
步骤5: 从模板HTML中提取设计基因
"""
import re
import logging
from typing import Dict, Any
from core.deepseek_client import DeepSeekClient
from prompts.design_prompts import STYLE_GENES_PROMPT

logger = logging.getLogger(__name__)


class StyleGeneExtractor:
    """设计基因提取器 - 保证风格一致性"""
    
    def __init__(self, client: DeepSeekClient = None):
        self.client = client or DeepSeekClient()
    
    async def extract_style_genes(self, template_html: str) -> str:
        """
        从模板HTML中提取核心设计基因
        
        Args:
            template_html: 模板HTML内容
            
        Returns:
            设计基因描述文本
        """
        # 方法1: AI分析提取
        try:
            ai_genes = await self._extract_with_ai(template_html)
            if ai_genes:
                return ai_genes
        except Exception as e:
            logger.warning(f"AI提取设计基因失败: {e}")
        
        # 方法2: CSS正则回退提取
        return self._extract_with_regex(template_html)
    
    async def _extract_with_ai(self, template_html: str) -> str:
        """使用AI分析提取设计基因"""
        prompt = STYLE_GENES_PROMPT.format(template_html=template_html[:3000])
        
        system_prompt = "你是一位专业的PPT设计师，擅长分析和提取设计基因。"
        
        response = self.client.chat(system_prompt, prompt, temperature=0.3)
        return response.strip()
    
    def _extract_with_regex(self, template_html: str) -> str:
        """使用正则表达式提取设计基因（回退方案）"""
        genes = []
        
        # 提取颜色
        bg_colors = re.findall(r'background(?:-color)?:\s*([^;]+);', template_html, re.IGNORECASE)
        colors = re.findall(r'(?<!background-)color:\s*([^;]+);', template_html, re.IGNORECASE)
        
        if bg_colors:
            unique_bgs = list(set([c.strip() for c in bg_colors[:5]]))
            genes.append(f"背景色：{', '.join(unique_bgs)}")
        if colors:
            unique_colors = list(set([c.strip() for c in colors[:5]]))
            genes.append(f"文字色：{', '.join(unique_colors)}")
        
        # 提取字体
        fonts = re.findall(r'font-family:\s*([^;]+);', template_html, re.IGNORECASE)
        if fonts:
            unique_fonts = list(set([f.strip() for f in fonts[:3]]))
            genes.append(f"字体：{', '.join(unique_fonts)}")
        
        # 提取字号
        font_sizes = re.findall(r'font-size:\s*([^;]+);', template_html, re.IGNORECASE)
        if font_sizes:
            unique_sizes = list(set([s.strip() for s in font_sizes[:5]]))
            genes.append(f"字号：{', '.join(unique_sizes)}")
        
        # 提取圆角
        border_radius = re.findall(r'border-radius:\s*([^;]+);', template_html, re.IGNORECASE)
        if border_radius:
            genes.append(f"圆角：{border_radius[0].strip()}")
        
        # 提取阴影
        box_shadows = re.findall(r'box-shadow:\s*([^;]+);', template_html, re.IGNORECASE)
        if box_shadows:
            genes.append(f"阴影：{box_shadows[0].strip()}")
        
        # 提取布局方式
        if 'display: flex' in template_html or 'display:flex' in template_html:
            genes.append("布局方式：Flexbox弹性布局")
        elif 'display: grid' in template_html or 'display:grid' in template_html:
            genes.append("布局方式：Grid网格布局")
        
        # 提取间距
        paddings = re.findall(r'padding(?:-top|-right|-bottom|-left)?:\s*([^;]+);', template_html, re.IGNORECASE)
        if paddings:
            genes.append(f"内边距：{paddings[0].strip()}")
        
        margins = re.findall(r'margin(?:-top|-right|-bottom|-left)?:\s*([^;]+);', template_html, re.IGNORECASE)
        if margins:
            genes.append(f"外边距：{margins[0].strip()}")
        
        return "\n".join(genes) if genes else "使用默认现代简约风格"
    
    def extract_as_dict(self, template_html: str) -> Dict[str, Any]:
        """
        提取设计基因并返回字典格式
        
        Returns:
            {
                "colors": {...},
                "fonts": {...},
                "layout": {...},
                "elements": {...}
            }
        """
        genes_text = self._extract_with_regex(template_html)
        
        result = {
            "colors": {},
            "fonts": {},
            "layout": {},
            "elements": {}
        }
        
        # 解析文本到字典
        for line in genes_text.split('\n'):
            if '背景色' in line:
                result["colors"]["background"] = line.split('：')[1] if '：' in line else ""
            elif '文字色' in line:
                result["colors"]["text"] = line.split('：')[1] if '：' in line else ""
            elif '字体' in line:
                result["fonts"]["family"] = line.split('：')[1] if '：' in line else ""
            elif '字号' in line:
                result["fonts"]["sizes"] = line.split('：')[1] if '：' in line else ""
            elif '圆角' in line:
                result["elements"]["border_radius"] = line.split('：')[1] if '：' in line else ""
            elif '阴影' in line:
                result["elements"]["box_shadow"] = line.split('：')[1] if '：' in line else ""
            elif '布局方式' in line:
                result["layout"]["type"] = line.split('：')[1] if '：' in line else ""
        
        return result
