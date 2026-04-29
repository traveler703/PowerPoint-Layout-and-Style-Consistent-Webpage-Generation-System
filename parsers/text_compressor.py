"""
长文本智能压缩模块。
当页面文本超过阈值时，调用 LLM 进行关键信息提取和压缩。
"""

from __future__ import annotations

import logging
from typing import Any

from parsers.base import BulletPoint, DocumentParseResult, PageContent

logger = logging.getLogger(__name__)

# 默认阈值配置
DEFAULT_PAGE_CHAR_THRESHOLD = 800  # 单页总字符数超过此值时触发压缩
DEFAULT_PARAGRAPH_CHAR_THRESHOLD = 300  # 单段落字符数超过此值时触发压缩


class TextCompressor:
    """
    利用 LLM 对长文本进行智能压缩。
    - 保留关键信息，提取为结构化要点
    - 保留原始文本用于回溯
    """

    def __init__(
        self,
        *,
        page_threshold: int = DEFAULT_PAGE_CHAR_THRESHOLD,
        paragraph_threshold: int = DEFAULT_PARAGRAPH_CHAR_THRESHOLD,
    ):
        self.page_threshold = page_threshold
        self.paragraph_threshold = paragraph_threshold

    async def compress_document(
        self, doc: DocumentParseResult
    ) -> DocumentParseResult:
        """
        对文档中超过阈值的页面进行压缩。

        Args:
            doc: 原始解析结果

        Returns:
            压缩后的文档（原始文本保留在 compressed_from 字段中）
        """
        compressed_pages: list[PageContent] = []

        for page in doc.pages:
            if page.text_length > self.page_threshold:
                compressed_page = await self._compress_page(page)
                compressed_pages.append(compressed_page)
            else:
                compressed_pages.append(page)

        doc.pages = compressed_pages
        return doc

    async def _compress_page(self, page: PageContent) -> PageContent:
        """压缩单个页面的长文本。"""
        from generator.llm_client import default_llm_client

        # 收集需要压缩的长段落
        long_paragraphs = [p for p in page.paragraphs if len(p) > self.paragraph_threshold]

        if not long_paragraphs and page.text_length <= self.page_threshold:
            return page

        # 构建压缩 prompt
        original_text = "\n".join(page.paragraphs) if page.paragraphs else page.raw_text
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(original_text, page.title)

        try:
            client = default_llm_client()
            response = await client.complete(system_prompt, user_prompt)
            compressed_bullets = self._parse_compression_result(response)

            # 创建压缩后的页面
            compressed_page = page.model_copy(deep=True)
            compressed_page.compressed = True
            compressed_page.compressed_from = original_text

            # 将长段落替换为压缩后的要点
            if compressed_bullets:
                # 保留短段落，移除长段落
                compressed_page.paragraphs = [
                    p for p in page.paragraphs if len(p) <= self.paragraph_threshold
                ]
                # 添加压缩得到的要点
                compressed_page.bullets = page.bullets + compressed_bullets

            logger.info(
                f"页面 {page.page_index} 压缩完成: "
                f"{page.text_length} -> {compressed_page.text_length} 字符"
            )
            return compressed_page

        except Exception as e:
            logger.warning(f"页面 {page.page_index} 压缩失败，保留原文: {e}")
            return page

    @staticmethod
    def _build_system_prompt() -> str:
        """构建压缩任务的系统提示词。"""
        return """你是一位专业的内容编辑助手。你的任务是将长段落文本压缩为简洁的要点列表。

要求：
1. 提取关键信息，每个要点不超过30个字
2. 保留核心观点和数据
3. 输出格式为每行一个要点，使用 "- " 开头
4. 要点数量控制在3-8个
5. 不要添加任何解释或前言，直接输出要点列表"""

    @staticmethod
    def _build_user_prompt(text: str, title: str | None = None) -> str:
        """构建用户消息。"""
        prompt = ""
        if title:
            prompt += f"页面标题：{title}\n\n"
        prompt += f"请将以下文本压缩为关键要点：\n\n{text}"
        return prompt

    @staticmethod
    def _parse_compression_result(response: str) -> list[BulletPoint]:
        """解析 LLM 返回的压缩结果为 BulletPoint 列表。"""
        bullets: list[BulletPoint] = []

        for line in response.strip().splitlines():
            line = line.strip()
            if not line:
                continue

            # 去掉列表标记
            if line.startswith(("-", "*", "•", "·")):
                line = line[1:].strip()
            elif line[0].isdigit() and ("." in line[:3] or "、" in line[:3]):
                # 编号列表 "1. xxx" 或 "1、xxx"
                line = line.split(".", 1)[-1].split("、", 1)[-1].strip()

            if not line:
                continue

            # 尝试分割为标题:描述
            if "：" in line:
                t, _, d = line.partition("：")
                bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
            elif ":" in line and len(line.split(":", 1)[0]) < 15:
                t, _, d = line.partition(":")
                bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
            else:
                bullets.append(BulletPoint(title=line, description=""))

        return bullets
