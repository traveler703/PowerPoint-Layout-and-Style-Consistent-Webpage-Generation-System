"""
HTML验证与修复服务 - LandPPT原版
步骤9: HTML验证与修复
参考: slide_html_inspection_service.py, layout_repair_service.py
"""
import re
import logging
from typing import Dict, Any, Tuple
from bs4 import BeautifulSoup
from collections import Counter

logger = logging.getLogger(__name__)

# 防溢出CSS注入
ANTI_OVERFLOW_CSS = """
/* 
 * 防内容溢出CSS - 防止LLM生成的overflow:hidden截断文字
 * 目标：只解锁"叶子级内容容器"的文字截断
 */

p, span, li, td, th, label,
h1, h2, h3, h4, h5, h6, a {
    text-overflow: unset !important;
    -webkit-line-clamp: unset !important;
}

[class*="card"] > *,
[class*="item"] > p, [class*="item"] > span,
[class*="tile"] > *, [class*="panel"] > *,
[class*="desc"], [class*="info"] > p {
    overflow: visible !important;
    text-overflow: unset !important;
    -webkit-line-clamp: unset !important;
}

.content-layer,
[data-content-layer],
.main-content,
[class*="slide-root"],
#canvas,
body > div {
    /* 保持原有overflow行为 */
}
"""


class HtmlValidatorService:
    """HTML验证与修复服务"""
    
    def __init__(self):
        self._critical_tags = {'html', 'head', 'body', 'div', 'p', 'span'}
        self._self_closing_tags = {'meta', 'link', 'img', 'br', 'hr', 'input', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'}
    
    def validate_html(self, html: str) -> Dict[str, Any]:
        """
        验证HTML完整性
        
        Returns:
            {
                'is_valid': bool,
                'errors': list,
                'warnings': list,
                'missing_elements': list
            }
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_elements': []
        }
        
        if not html or not html.strip():
            result['is_valid'] = False
            result['errors'].append('HTML内容为空或仅包含空白字符')
            return result
        
        # 检查HTML语法
        self._check_html_well_formedness(html, result)
        
        # 检查必需元素
        self._check_required_elements(html, result)
        
        result['is_valid'] = len(result['errors']) == 0
        
        return result
    
    def _check_html_well_formedness(self, html: str, result: Dict) -> None:
        """检查HTML语法"""
        try:
            from lxml import etree
            encoded_html = html.encode('utf-8')
            parser = etree.HTMLParser(recover=False, encoding='utf-8')
            etree.fromstring(encoded_html, parser)
        except ImportError:
            logger.warning('lxml不可用，使用基础HTML验证')
            self._basic_html_syntax_check(html, result)
        except Exception as e:
            result['errors'].append(f'HTML语法错误: {str(e)}')
    
    def _basic_html_syntax_check(self, html: str, result: Dict) -> None:
        """基础HTML语法检查"""
        # 检查格式错误的标签
        malformed_tags = re.findall(r'<[^>]*<[^>]*>', html)
        if malformed_tags:
            result['errors'].append('发现格式错误的标签')
        
        # 检查未闭合的关键标签
        open_tags = re.findall('<([a-zA-Z][a-zA-Z0-9]*)[^>]*>', html)
        close_tags = re.findall('</([a-zA-Z][a-zA-Z0-9]*)>', html)
        
        open_tag_counts = Counter([tag.lower() for tag in open_tags if tag.lower() in self._critical_tags])
        close_tag_counts = Counter([tag.lower() for tag in close_tags if tag.lower() in self._critical_tags])
        
        for tag, open_count in open_tag_counts.items():
            close_count = close_tag_counts.get(tag, 0)
            if open_count > close_count:
                result['errors'].append(f'未闭合的关键HTML标签: {tag}')
    
    def _check_required_elements(self, html: str, result: Dict) -> None:
        """检查必需元素"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 检查html/body标签
        if not soup.find('html'):
            result['warnings'].append('缺少<html>标签')
        
        if not soup.find('body'):
            result['warnings'].append('缺少<body>标签')
        
        # 检查div标签
        if not soup.find('div'):
            result['warnings'].append('缺少<div>标签')
        
        # 检查标签顺序
        html_tag = soup.find('html')
        body_tag = soup.find('body')
        if html_tag and body_tag:
            html_index = list(soup.children).index(html_tag) if html_tag in soup.children else -1
            body_index = list(soup.children).index(body_tag) if body_tag in soup.children else -1
            if body_index > 0 and html_index > body_index:
                result['warnings'].append('<body>标签出现在<html>标签之前')
        
        # 检查未转义的特殊字符
        text_content = soup.get_text()
        if '<' in text_content or '>' in text_content:
            result['warnings'].append("文本内容中可能包含未转义的特殊字符")
    
    def fix_html(self, html: str) -> str:
        """
        自动修复HTML
        
        Args:
            html: 原始HTML
            
        Returns:
            修复后的HTML
        """
        try:
            from lxml import etree
            
            # 尝试严格模式解析
            encoded_html = html.encode('utf-8')
            strict_parser = etree.HTMLParser(recover=False, encoding='utf-8')
            
            try:
                etree.fromstring(encoded_html, strict_parser)
                logger.debug('HTML已经是有效的，无需修复')
                return html
            except:
                pass
            
            # 使用恢复模式解析
            recover_parser = etree.HTMLParser(recover=True, encoding='utf-8')
            tree = etree.fromstring(encoded_html, recover_parser)
            
            # 生成修复后的HTML
            fixed_html = etree.tostring(tree, encoding='unicode', method='html', pretty_print=True)
            
            # 保留原始DOCTYPE
            doctype_match = re.search(r'<!doctype[^>]*>', html, re.IGNORECASE)
            if doctype_match:
                doctype = doctype_match.group(0)
                if not fixed_html.lower().startswith('<!doctype'):
                    fixed_html = doctype + '\n' + fixed_html
            
            logger.info('HTML已自动修复')
            return fixed_html
            
        except ImportError:
            logger.warning('lxml不可用，跳过自动修复')
            return html
        except Exception as e:
            logger.error(f'HTML自动修复失败: {e}')
            return html
    
    def inject_anti_overflow_css(self, html: str) -> str:
        """
        注入防溢出CSS
        
        Args:
            html: HTML内容
            
        Returns:
            注入CSS后的HTML
        """
        if '<style' in html.lower():
            # 追加到现有style
            style_match = re.search(r'(<style[^>]*>)([\s\S]*?)(</style>)', html, re.IGNORECASE)
            if style_match:
                new_style = style_match.group(1) + '\n' + ANTI_OVERFLOW_CSS + style_match.group(2) + style_match.group(3)
                html = html[:style_match.start()] + new_style + html[style_match.end():]
        else:
            # 添加新的style标签
            style_tag = f'<style>\n{ANTI_OVERFLOW_CSS}\n</style>'
            
            if '<head>' in html.lower():
                html = re.sub(
                    r'(<head[^>]*>)',
                    r'\1\n' + style_tag,
                    html,
                    count=1,
                    flags=re.IGNORECASE
                )
            else:
                # 添加到html标签后
                html = re.sub(
                    r'(<html[^>]*>)',
                    r'\1\n<head>\n' + style_tag + '\n</head>',
                    html,
                    count=1,
                    flags=re.IGNORECASE
                )
        
        return html
    
    def validate_and_fix(self, html: str) -> Tuple[str, Dict[str, Any]]:
        """
        验证并修复HTML
        
        Args:
            html: 原始HTML
            
        Returns:
            (修复后的HTML, 验证结果)
        """
        # 1. 验证
        validation_result = self.validate_html(html)
        
        # 2. 修复语法错误
        if not validation_result['is_valid']:
            html = self.fix_html(html)
            # 重新验证
            validation_result = self.validate_html(html)
        
        # 3. 注入防溢出CSS
        html = self.inject_anti_overflow_css(html)
        
        return html, validation_result
