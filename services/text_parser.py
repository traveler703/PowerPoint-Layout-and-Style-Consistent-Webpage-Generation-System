"""
文本解析服务 - LandPPT
将用户输入的文本解析为结构化的大纲数据
"""
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TextParser:
    """文本解析器"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        解析文本内容
        
        Args:
            text: 用户输入的原始文本
            
        Returns:
            解析后的结构化数据
        """
        if not text:
            return self._empty_result()
        
        text = text.strip()
        
        # 尝试解析JSON格式
        if text.startswith('{') or text.startswith('['):
            try:
                import json
                data = json.loads(text)
                return self._process_structured_data(data)
            except json.JSONDecodeError:
                pass
        
        # 解析Markdown格式
        if self._is_markdown(text):
            return self._parse_markdown(text)
        
        # 解析普通文本
        return self._parse_plain_text(text)
    
    def _empty_result(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'title': '未命名文档',
            'summary': '',
            'sections': []
        }
    
    def _is_markdown(self, text: str) -> bool:
        """判断是否为Markdown格式"""
        markdown_indicators = [
            r'^#+\s+',           # 标题
            r'^\d+\.\s+',        # 有序列表
            r'^[-*+]\s+',        # 无序列表
            r'^\[\s*[xX]?\s*\]',# 复选框
        ]
        for pattern in markdown_indicators:
            if re.search(pattern, text, re.MULTILINE):
                return True
        return False
    
    def _parse_markdown(self, text: str) -> Dict[str, Any]:
        """解析Markdown格式文本"""
        lines = text.split('\n')
        
        title = ''
        summary = ''
        sections = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 一级标题
            h1_match = re.match(r'^#\s+(.+)$', line)
            if h1_match:
                title = h1_match.group(1).strip()
                continue
            
            # 二级标题
            h2_match = re.match(r'^##\s+(.+)$', line)
            if h2_match:
                if current_section:
                    sections.append(current_section)
                current_section = {
                    'title': h2_match.group(1).strip(),
                    'content': '',
                    'bullets': []
                }
                continue
            
            # 三级标题
            h3_match = re.match(r'^###\s+(.+)$', line)
            if h3_match:
                if current_section:
                    if current_section['content']:
                        current_section['content'] += '\n' + h3_match.group(1).strip()
                    else:
                        current_section['content'] = h3_match.group(1).strip()
                continue
            
            # 有序列表
            ol_match = re.match(r'^\d+\.\s+(.+)$', line)
            if ol_match:
                content = ol_match.group(1).strip()
                # 移除加粗等格式
                content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
                content = re.sub(r'\*(.+?)\*', r'\1', content)
                content = re.sub(r'`(.+?)`', r'\1', content)
                
                if current_section:
                    current_section['bullets'].append(content)
                continue
            
            # 无序列表
            ul_match = re.match(r'^[-*+]\s+(.+)$', line)
            if ul_match:
                content = ul_match.group(1).strip()
                content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
                content = re.sub(r'\*(.+?)\*', r'\1', content)
                content = re.sub(r'`(.+?)`', r'\1', content)
                
                if current_section:
                    current_section['bullets'].append(content)
                continue
            
            # 复选框
            checkbox_match = re.match(r'^\[\s*[xX]?\s*\]\s*(.+)$', line)
            if checkbox_match:
                content = checkbox_match.group(1).strip()
                content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
                if current_section:
                    current_section['bullets'].append(content)
                continue
            
            # 普通段落
            if current_section:
                if current_section['content']:
                    current_section['content'] += ' ' + line
                else:
                    current_section['content'] = line
            elif not title and line:
                # 第一个非列表内容作为摘要
                summary = line
        
        if current_section:
            sections.append(current_section)
        
        # 如果没有提取到标题，使用第一行
        if not title and lines:
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    title = line[:50] + ('...' if len(line) > 50 else '')
                    break
        
        return {
            'title': title or '未命名文档',
            'summary': summary,
            'sections': sections
        }
    
    def _parse_plain_text(self, text: str) -> Dict[str, Any]:
        """解析普通文本格式"""
        lines = text.split('\n')
        
        title = ''
        summary = ''
        sections = []
        current_section = None
        current_bullets = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 检测标题模式
            # 模式1: "一、二、三" 或 "第一、第二"
            section_pattern_1 = re.match(r'^[一二三四五六七八九十]+[、.]\s*(.+)$', line)
            # 模式2: "第X部分" 或 "第X章"
            section_pattern_2 = re.match(r'^第[一二三四五六七八九十\d]+[部分章节节]\s*[:：]?\s*(.*)$', line)
            # 模式3: "1. " 或 "1) " 开头的行
            section_pattern_3 = re.match(r'^(\d+)[.)]\s+(.+)$', line)
            
            if section_pattern_1:
                if current_section:
                    current_section['bullets'] = current_bullets.copy()
                    sections.append(current_section)
                title = section_pattern_1.group(1).strip()
                current_section = {
                    'title': title,
                    'content': '',
                    'bullets': []
                }
                current_bullets = []
                continue
            
            if section_pattern_2:
                if current_section:
                    current_section['bullets'] = current_bullets.copy()
                    sections.append(current_section)
                section_title = section_pattern_2.group(1) or section_pattern_2.group(0)
                current_section = {
                    'title': section_title.strip(),
                    'content': '',
                    'bullets': []
                }
                current_bullets = []
                continue
            
            if section_pattern_3:
                if current_section:
                    current_section['bullets'] = current_bullets.copy()
                    sections.append(current_section)
                current_section = {
                    'title': section_pattern_3.group(2).strip(),
                    'content': '',
                    'bullets': []
                }
                current_bullets = []
                continue
            
            # 检测要点模式
            bullet_pattern = re.match(r'^[-•*]\s+(.+)$', line)
            if bullet_pattern:
                current_bullets.append(bullet_pattern.group(1).strip())
                continue
            
            # 普通段落
            if current_section:
                if current_section['content']:
                    current_section['content'] += ' ' + line
                else:
                    current_section['content'] = line
            else:
                # 作为摘要
                if summary:
                    summary += ' ' + line
                else:
                    summary = line
        
        # 添加最后一个section
        if current_section:
            current_section['bullets'] = current_bullets.copy()
            sections.append(current_section)
        
        # 如果没有提取到标题，尝试从第一行获取
        if not title and lines:
            for line in lines:
                line = line.strip()
                if line and len(line) > 3:
                    # 跳过太短的内容
                    if len(line) < 10:
                        continue
                    title = line[:60] + ('...' if len(line) > 60 else '')
                    break
        
        return {
            'title': title or '未命名文档',
            'summary': summary,
            'sections': sections
        }
    
    def _process_structured_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理已经是结构化的数据"""
        if isinstance(data, dict):
            return {
                'title': data.get('title', '未命名文档'),
                'summary': data.get('summary', data.get('description', '')),
                'sections': data.get('sections', data.get('chapters', []))
            }
        
        if isinstance(data, list):
            # 假设是段落列表
            return {
                'title': '结构化文档',
                'summary': '',
                'sections': [{'title': f'第{i+1}部分', 'content': item, 'bullets': []} 
                           for i, item in enumerate(data) if isinstance(item, str)]
            }
        
        return self._empty_result()
