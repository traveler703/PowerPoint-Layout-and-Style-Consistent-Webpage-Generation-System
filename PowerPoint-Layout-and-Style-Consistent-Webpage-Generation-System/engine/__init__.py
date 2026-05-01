"""
Engine 模块 - 数据类型定义

主要导出：
- SemanticPageInput: 单页语义输入
- ContentPageInput, SectionInput, PresentationOutline: 流水线数据类型
- GenerationResult: 生成结果
"""

from engine.types import (
    BulletItem,
    HeadingBlock,
    SemanticPageInput,
    TableData,
)

# 流水线数据类型（定义在 pipeline.py）
# 使用时从 pipeline 导入：
# from pipeline import (
#     ContentPageInput,
#     SectionInput,
#     PresentationOutline,
#     GenerationResult,
#     PresentationGenerator,
#     generate_presentation,
# )

__all__ = [
    # 核心类型
    "SemanticPageInput",
    "HeadingBlock",
    "BulletItem",
    "TableData",
]
