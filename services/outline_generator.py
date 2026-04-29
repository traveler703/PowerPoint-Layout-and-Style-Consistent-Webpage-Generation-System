"""
大纲生成服务 - LandPPT原版
步骤2-3: 生成大纲 + 验证/修复大纲
"""
import json
import logging
from typing import Dict, Any, Optional
from core.deepseek_client import DeepSeekClient
from prompts.outline_prompts import OUTLINE_PROMPT, OUTLINE_VALIDATION_PROMPT

logger = logging.getLogger(__name__)


class OutlineGenerator:
    """大纲生成器 - 步骤2-3"""
    
    def __init__(self, client: DeepSeekClient = None):
        self.client = client or DeepSeekClient()
    
    async def generate_outline(
        self,
        topic: str,
        scenario: str = "general",
        audience: str = "通用受众",
        page_count: int = 10
    ) -> Dict[str, Any]:
        """
        生成PPT大纲
        
        Args:
            topic: 主题
            scenario: 场景类型
            audience: 受众
            page_count: 页数
            
        Returns:
            大纲JSON
        """
        logger.info(f"开始生成大纲: topic={topic}, page_count={page_count}")
        
        try:
            # 步骤2: 生成大纲
            prompt = OUTLINE_PROMPT.format(
                topic=topic,
                scenario=scenario,
                audience=audience,
                page_count=page_count
            )
            
            system_prompt = """你是一位专业的PPT大纲策划专家。
请根据用户需求生成结构清晰、内容丰富的PPT大纲。
必须返回有效的JSON格式，不要包含任何解释文字。"""
            
            response = self.client.chat(system_prompt, prompt, temperature=0.7)
            
            # 解析JSON
            outline = self._parse_json_response(response)
            
            # 步骤3: 验证并修复大纲
            validated_outline = await self.validate_and_fix_outline(outline, page_count)
            
            logger.info(f"大纲生成成功: {len(validated_outline.get('slides', []))}页")
            return validated_outline
            
        except Exception as e:
            logger.error(f"生成大纲失败: {e}")
            raise ValueError(f"生成大纲失败: {e}")
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应"""
        response = response.strip()
        
        # 尝试提取代码块中的JSON
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
        if json_match:
            response = json_match.group(1)
        else:
            # 尝试直接解析
            json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
            if json_match:
                response = json_match.group(1)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise ValueError(f"无法解析JSON响应: {e}")
    
    async def validate_and_fix_outline(
        self, 
        outline: Dict[str, Any], 
        expected_page_count: int
    ) -> Dict[str, Any]:
        """
        验证并修复大纲
        
        Args:
            outline: 原始大纲
            expected_page_count: 期望的页数
            
        Returns:
            验证并修复后的大纲
        """
        try:
            prompt = OUTLINE_VALIDATION_PROMPT.format(
                outline_json=json.dumps(outline, ensure_ascii=False, indent=2)
            )
            
            system_prompt = """你是一位专业的PPT大纲审核员。
请验证大纲的有效性，并修复发现的问题。
必须返回有效的JSON格式。"""
            
            response = self.client.chat(system_prompt, prompt, temperature=0.3)
            
            # 解析响应
            fixed_outline = self._parse_json_response(response)
            
            # 额外验证和修复
            fixed_outline = self._fix_outline_issues(fixed_outline, expected_page_count)
            
            return fixed_outline
            
        except Exception as e:
            logger.warning(f"大纲验证失败，使用原始大纲: {e}")
            return self._fix_outline_issues(outline, expected_page_count)
    
    def _fix_outline_issues(
        self, 
        outline: Dict[str, Any], 
        expected_page_count: int
    ) -> Dict[str, Any]:
        """修复大纲问题"""
        if not isinstance(outline, dict):
            raise ValueError("大纲必须是字典格式")
        
        # 确保有title字段
        if 'title' not in outline:
            outline['title'] = "PPT演示文稿"
        
        # 确保有slides字段
        if 'slides' not in outline:
            outline['slides'] = []
        
        slides = outline['slides']
        if not isinstance(slides, list):
            slides = []
            outline['slides'] = slides
        
        # 修复页数问题
        current_count = len(slides)
        
        if current_count < expected_page_count:
            # 添加缺失的页
            for i in range(current_count, expected_page_count):
                slides.append({
                    "page_number": i + 1,
                    "title": f"内容页 {i + 1}",
                    "content_points": ["要点1", "要点2"],
                    "slide_type": "content"
                })
        elif current_count > expected_page_count:
            # 截断多余的页
            slides = slides[:expected_page_count]
            outline['slides'] = slides
        
        # 确保slide_type正确
        if slides:
            # 第1页必须是title
            slides[0]['slide_type'] = 'title'
            slides[0]['page_number'] = 1
            
            # 最后一页必须是conclusion或thankyou
            slides[-1]['slide_type'] = 'conclusion'
            slides[-1]['page_number'] = len(slides)
        
        # 重新编号
        for i, slide in enumerate(slides):
            slide['page_number'] = i + 1
        
        return outline
    
    def extract_slides_for_generation(self, outline: Dict[str, Any]) -> list:
        """从大纲中提取用于生成的幻灯片数据"""
        slides = outline.get('slides', [])
        
        result = []
        for slide in slides:
            result.append({
                'page_number': slide.get('page_number', 1),
                'title': slide.get('title', ''),
                'content_points': slide.get('content_points', []),
                'slide_type': slide.get('slide_type', 'content')
            })
        
        return result
    
    def parse_manual_outline(self, title: str, outline_text: str) -> Dict[str, Any]:
        """
        解析手动输入的大纲文本
        
        支持多种格式：
        1. 第X页 类型: 标题
        2. 第X页 标题（标题直接跟在页码后面）
        3. 第X页 类型（换行）标题
        
        Args:
            title: PPT标题
            outline_text: 大纲文本
            
        Returns:
            大纲JSON
        """
        import re
        
        slides = []
        
        # 类型列表
        known_types = ['封面', '目录', '内容', '章节', '结论', '感谢', 'title', 'agenda', 'content', 'section_header', 'conclusion', 'thankyou']
        
        # 类型映射
        type_mapping = {
            '封面': 'title', 'title': 'title',
            '目录': 'agenda', 'agenda': 'agenda',
            '内容': 'content', 'content': 'content',
            '章节': 'section_header', 'section_header': 'section_header',
            '结论': 'conclusion', 'conclusion': 'conclusion',
            '感谢': 'thankyou', 'thankyou': 'thankyou'
        }
        
        # 先按页分割 - 支持 "第X页" 开头的新页
        # 格式: 第1页 [类型] [标题] 或 第1页 标题（没有类型）
        page_pattern = re.compile(r'第(\d+)页\s+([^\n]+)')
        
        # 找到所有页面开始的位置
        page_starts = []
        for match in page_pattern.finditer(outline_text):
            page_line = match.group(2).strip()
            
            # 分离类型和标题
            slide_type = 'content'  # 默认类型
            slide_title = ''
            
            # 检查是否有已知类型关键字
            found_type = None
            for t in known_types:
                if page_line.startswith(t):
                    found_type = t
                    rest = page_line[len(t):].strip()
                    if rest.startswith(':') or rest.startswith('：'):
                        rest = rest[1:].strip()
                    slide_title = rest
                    break
            
            if found_type:
                slide_type = type_mapping.get(found_type, 'content')
            else:
                # 没有已知类型，整个就是标题
                slide_title = page_line
                # 尝试推断类型
                if '封面' in slide_title or '首页' in slide_title:
                    slide_type = 'title'
                elif '目录' in slide_title or '导览' in slide_title:
                    slide_type = 'agenda'
                elif '总结' in slide_title or '结语' in slide_title or '展望' in slide_title:
                    slide_type = 'conclusion'
                elif '感谢' in slide_title or '结束' in slide_title:
                    slide_type = 'thankyou'
            
            page_starts.append({
                'pos': match.start(),
                'page_num': int(match.group(1)),
                'type': slide_type,
                'title': slide_title.strip(':：').strip(),
                'match': match
            })
        
        # 解析每一页的内容
        for idx, page_info in enumerate(page_starts):
            start_pos = page_info['pos']
            slide_type = page_info['type']
            slide_title = page_info['title']
            
            # 确定结束位置
            if idx + 1 < len(page_starts):
                end_pos = page_starts[idx + 1]['pos']
            else:
                end_pos = len(outline_text)
            
            # 提取页面内容
            page_content = outline_text[start_pos:end_pos]
            
            # 解析标题和要点
            lines = page_content.split('\n')
            
            if not slide_title:
                # 从后续行中找标题
                for line in lines[1:]:
                    line = line.strip()
                    if line and not line.startswith(('-', '•', '*', '第')):
                        slide_title = line
                        break
            
            content_points = []
            found_points = False
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('第'):
                    continue
                
                if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    point = line.lstrip('-•*').strip()
                    if point:
                        content_points.append(point)
                        found_points = True
                elif found_points and line:
                    # 在要点之后，继续收集
                    content_points.append(line)
            
            slides.append({
                'title': slide_title,
                'slide_type': slide_type,
                'content_points': content_points
            })
        
        # 重新编号
        for i, slide in enumerate(slides):
            slide['page_number'] = i + 1
        
        # 如果没有幻灯片，创建一个默认的
        if not slides:
            slides.append({
                'page_number': 1,
                'title': title,
                'slide_type': 'title',
                'content_points': []
            })
        
        # 确保第1页是封面，最后一页是结论
        if slides:
            slides[0]['slide_type'] = 'title'
            slides[-1]['slide_type'] = 'conclusion'
        
        return {
            'title': title,
            'slides': slides
        }

