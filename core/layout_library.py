"""
版式方法库 - LandPPT核心策略
指导AI选择合适的版式
"""
from typing import List, Dict

# 高级版式方法库
LAYOUT_METHODS = """
**高级版式方法库**

【栅格系统】
- 模块化栅格：3x3、4x2适合卡片展示
- 分栏网格：12栏系统，适合不对称切分
- 基线网格：控制多行文本纵向节律

【视觉动线】
- F型动线：适合文字密集页，视线从左上向右下
- Z型动线：适合图文交替页，视线之字形移动
- 第一落幅：页面上方1/3处建立视觉锚点

【版式结构】
- 三分法则：焦点放在四条线的交叉点(黄金分割点)
- 非对称平衡：左右体积不等但视觉重量平衡
- 黄金比例：1:1.618分割主副区域
- 仪表盘布局：适合总结/结论页，多数据并列
- 单栏叙事：适合故事性强的内容，从上到下阅读
- 双栏对比：适合对比类内容，左右分栏

【对齐微排版】
- 悬挂式缩进：序号悬挂形成视觉引导
- 纵向节律：行高与字号保持1.4-1.6倍比例
- 视觉层级跃升：主标题与正文字号比例至少1:0.6
- 左对齐基准：中文文本左对齐，英文可两端对齐

【避免的布局】
- 四宫格均质化：四个内容块等分，视觉单调
- 中心放射状：所有元素向中心聚集，拥挤
- 棋盘式：元素机械排列，缺少层次

【推荐版式组合】
- 封面：居中大标题 + 装饰元素
- 目录：左侧标题 + 右侧列表
- 内容页：标题 + 正文/卡片/图表
- 对比页：左右双栏
- 总结页：仪表盘/卡片网格
"""

# 幻灯片类型与推荐版式映射
SLIDE_TYPE_LAYOUTS = {
    "title": ["centered", "split", "full_background"],
    "agenda": ["left_list", "grid", "timeline"],
    "content": ["single_column", "two_column", "card_grid", "dashboard"],
    "conclusion": ["summary_cards", "centered", "timeline"],
    "thankyou": ["centered", "contact"]
}


class LayoutLibrary:
    """版式方法库管理器"""
    
    @staticmethod
    def get_layout_methods() -> str:
        """获取完整版式方法库"""
        return LAYOUT_METHODS
    
    @staticmethod
    def get_layout_for_slide_type(slide_type: str) -> List[str]:
        """获取指定幻灯片类型推荐的版式"""
        return SLIDE_TYPE_LAYOUTS.get(slide_type, ["single_column"])
    
    @staticmethod
    def get_layout_suggestion(slide_type: str, content_count: int) -> str:
        """根据内容数量生成版式建议"""
        layouts = LayoutLibrary.get_layout_for_slide_type(slide_type)
        
        if content_count == 1:
            return "single_column or centered"
        elif content_count == 2:
            return "two_column"
        elif content_count <= 4:
            return "card_grid or dashboard"
        else:
            return "left_list or timeline"
    
    @staticmethod
    def get_visual_principles() -> List[str]:
        """获取视觉设计原则"""
        return [
            "建立明确的视觉层次：标题 > 副标题 > 正文 > 注释",
            "保持留白空间：内容区填充率控制在60-80%",
            "使用重复的设计元素建立节奏感",
            "对比度要足够：文字与背景对比度至少4.5:1",
            "避免视觉噪音：每页聚焦一个核心信息"
        ]
