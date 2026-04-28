"""
全局宪法生成模块 - LandPPT原版
步骤6: 生成指导整份PPT的全局宪法
"""
import logging
from typing import List, Dict, Any
from core.deepseek_client import DeepSeekClient
from prompts.design_prompts import CONSTITUTION_PROMPT

logger = logging.getLogger(__name__)


class GlobalConstitutionGenerator:
    """全局宪法生成器 - 保证内容丰富度和风格一致"""
    
    def __init__(self, client: DeepSeekClient = None):
        self.client = client or DeepSeekClient()
    
    async def generate_constitution(
        self,
        topic: str,
        scenario: str,
        style: str,
        all_slides: List[Dict[str, Any]],
        style_genes: str
    ) -> str:
        """
        生成全局宪法
        
        Args:
            topic: PPT主题
            scenario: 场景类型
            style: 风格类型
            all_slides: 所有幻灯片大纲
            style_genes: 设计基因
            
        Returns:
            全局宪法文本
        """
        # 生成大纲摘要
        slides_summary = self._generate_slides_summary(all_slides)
        
        try:
            # 使用AI生成
            prompt = CONSTITUTION_PROMPT.format(
                topic=topic,
                scenario=scenario,
                style=style,
                page_count=len(all_slides),
                style_genes=style_genes,
                slides_summary=slides_summary
            )
            
            system_prompt = """你是一位专业的PPT设计策略师，负责生成全局设计宪法。
全局宪法将指导整份PPT的生成，确保内容丰富、风格一致、排版专业。"""
            
            response = self.client.chat(system_prompt, prompt, temperature=0.7)
            return response.strip()
            
        except Exception as e:
            logger.error(f"生成全局宪法失败: {e}")
            # 返回默认宪法
            return self._get_default_constitution(topic, len(all_slides))
    
    def _generate_slides_summary(self, slides: List[Dict[str, Any]]) -> str:
        """生成幻灯片摘要"""
        summary_parts = []
        
        for slide in slides:
            slide_type = slide.get('slide_type', 'content')
            title = slide.get('title', '')
            points = slide.get('content_points', [])
            
            if slide_type == 'title':
                summary_parts.append(f"- 封面：{title}")
            elif slide_type == 'agenda':
                summary_parts.append(f"- 目录：{title}")
            elif slide_type == 'section_header':
                summary_parts.append(f"- 章节页：{title}")
            elif slide_type == 'conclusion':
                summary_parts.append(f"- 结论页：{title}")
            elif slide_type == 'thankyou':
                summary_parts.append(f"- 感谢页")
            else:
                point_count = len(points)
                summary_parts.append(f"- {title}（{point_count}个要点）")
        
        return "\n".join(summary_parts)
    
    def _get_default_constitution(self, topic: str, page_count: int) -> str:
        """获取默认宪法"""
        return f"""**全局设计宪法 - {topic}**

**内容深度策略**：
- 封面页：使用有力的一句话作为副标题，吸引注意力
- 内容页：每页聚焦2-4个核心要点，避免信息过载
- 结论页：总结3-5个核心记忆点

**视觉节奏规划**：
- 整体节奏：封面(1页) → 目录(1页) → 内容(60%) → 结论(1页)
- 避免连续3页使用相同版式
- 适当使用章节分隔页划分内容模块

**装饰元素使用原则**：
- 数据页：使用图表或图标强调数字
- 概念页：使用图形或色块辅助理解
- 案例页：使用卡片式布局展示多个案例

**排版规范**：
- 标题字号：36-48px
- 正文字号：18-24px
- 行高：1.4-1.6倍字号
- 页边距：40-60px

**一致性保证**：
- 全局使用统一的配色方案
- 标题样式统一（左对齐或居中）
- 页码格式统一（底部居中或右下角）
"""
