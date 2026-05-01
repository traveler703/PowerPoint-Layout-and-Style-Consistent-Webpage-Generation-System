"""
HTML清理服务 - LandPPT原版
步骤8: HTML清理与格式化
参考: slide_html_cleanup_service.py
"""
import re
import logging

logger = logging.getLogger(__name__)


class HtmlCleanupService:
    """HTML清理服务 - 清理AI响应"""
    
    @staticmethod
    def cleanup_html_response(raw_content: str) -> str:
        """
        清理AI响应，提取纯净HTML
        
        Args:
            raw_content: 原始AI响应
            
        Returns:
            清理后的HTML
        """
        if not raw_content:
            logger.warning("收到空响应")
            return ""
        
        # 1. 去除<think>标签内容
        raw_content = HtmlCleanupService._strip_think_tags(raw_content)
        
        content = raw_content.strip()
        logger.debug(f"原始AI响应长度: {len(content)}, 预览: {content[:200]}")
        
        content_lower = content.lower()
        
        # 检查响应是否过短
        if len(content) < 100:
            logger.warning(f"AI响应过短 ({len(content)} 字符)，可能不完整")
        
        # 检查是否有错误指示
        has_error = any(
            indicator in content_lower 
            for indicator in ["error", "sorry", "cannot", "unable", "apologize"]
        )
        if has_error:
            logger.warning("AI响应包含错误指示")
        
        # 2. 提取HTML代码块
        html_match = re.search(
            r'```html\s*\n?(.*?)\n?```',
            content, 
            re.DOTALL | re.IGNORECASE
        )
        if html_match:
            logger.debug("从markdown代码块中提取HTML")
            return html_match.group(1).strip()
        
        # 尝试通用代码块
        generic_match = re.search(
            r'```\s*\n?(.*?)\n?```',
            content,
            re.DOTALL
        )
        if generic_match:
            potential_html = generic_match.group(1).strip()
            # 检查是否像HTML
            if potential_html.lower().startswith('<!doctype') or \
               potential_html.lower().startswith('<html') or \
               potential_html.lower().startswith('<div'):
                logger.debug("从通用代码块中提取HTML")
                return potential_html
        
        # 3. 尝试直接提取HTML标签
        html_tag_match = re.search(
            r'(<!doctype[\s\S]*?</html>|<html[\s\S]*?</html>|<div[\s\S]*?)',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if html_tag_match:
            logger.debug("直接提取HTML标签")
            return html_tag_match.group(1).strip()
        
        # 4. 如果以上都失败，返回原始内容
        logger.warning("未能从响应中提取HTML，返回原始内容")
        return content
    
    @staticmethod
    def _strip_think_tags(content: str) -> str:
        """去除<think>标签内容"""
        # 去除<think>...</think>标签
        content = re.sub(
            r'<think>[\s\S]*?</think>',
            '',
            content,
            flags=re.IGNORECASE
        )
        
        # 去除<think>...</think>标签
        content = re.sub(
            r'<think>[\s\S]*?</think>',
            '',
            content,
            flags=re.IGNORECASE
        )
        
        return content
    
    @staticmethod
    def validate_html_length(html: str, min_length: int = 100) -> bool:
        """验证HTML长度是否足够"""
        if len(html) < min_length:
            logger.warning(f"HTML长度不足: {len(html)} < {min_length}")
            return False
        return True
    
    @staticmethod
    def extract_body_content(html: str) -> str:
        """提取body标签内容"""
        body_match = re.search(
            r'<body[^>]*>([\s\S]*?)</body>',
            html,
            re.IGNORECASE
        )
        if body_match:
            return body_match.group(1)
        return html
