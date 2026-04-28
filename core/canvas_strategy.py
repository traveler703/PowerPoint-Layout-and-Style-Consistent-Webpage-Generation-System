"""
固定画布策略 - LandPPT核心策略
确保每页不凌乱，元素正确排版
"""
from config import CANVAS_WIDTH, CANVAS_HEIGHT, HEADER_HEIGHT, FOOTER_HEIGHT

# 固定画布策略常量
FIXED_CANVAS_CONSTRAINTS = """
**固定画布策略**

画布尺寸：{width}px × {height}px (16:9比例)

三段式结构：
┌────────────────────────────────────┐
│           HEADER ({header}px)       │  固定页眉
├────────────────────────────────────┤
│                                    │
│           MAIN CONTENT             │  弹性主体区
│        (自适应内容高度)             │
│                                    │
├────────────────────────────────────┤
│           FOOTER ({footer}px)       │  固定页脚
└────────────────────────────────────┘

锚点稳定性规则：
1. 标题区 (Header) - 位置和层级固定，高度{header}px
2. 页码区 (Footer) - 位置固定，高度{footer}px
3. 主内容区 (Main) - 负责吸收空间变化

溢出处理优先级（按顺序执行）：
1. 删除/合并重复内容
2. 分组相关内容
3. 限制容器高度 (max-height)
4. 收紧间距 (padding/margin)
5. 缩小字号 (最小12px)
6. 禁用溢出滚动条 (overflow: hidden)

禁止事项：
- 禁止出现滚动条
- 禁止内容超出画布边界
- 禁止固定高度导致内容被截断
- 禁止使用text-overflow: ellipsis截断正文

CSS安全边界：
```css
.slide-canvas {{
    width: {width}px;
    height: {height}px;
    overflow: hidden;
    position: relative;
}}
.header {{ height: {header}px; }}
.main-content {{ height: auto; max-height: {main_height}px; }}
.footer {{ height: {footer}px; }}
```
""".format(
    width=CANVAS_WIDTH,
    height=CANVAS_HEIGHT,
    header=HEADER_HEIGHT,
    footer=FOOTER_HEIGHT,
    main_height=CANVAS_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT
)


class CanvasStrategy:
    """固定画布策略管理器"""
    
    @staticmethod
    def get_canvas_size() -> tuple:
        """获取画布尺寸"""
        return (CANVAS_WIDTH, CANVAS_HEIGHT)
    
    @staticmethod
    def get_section_sizes() -> dict:
        """获取各区域尺寸"""
        return {
            "header": HEADER_HEIGHT,
            "footer": FOOTER_HEIGHT,
            "main_height": CANVAS_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT,
            "total": CANVAS_HEIGHT
        }
    
    @staticmethod
    def get_constraints() -> str:
        """获取完整约束文本"""
        return FIXED_CANVAS_CONSTRAINTS
    
    @staticmethod
    def get_overflow_priority() -> list:
        """获取溢出处理优先级"""
        return [
            "delete_merge",      # 删除/合并内容
            "group",             # 分组内容
            "limit_height",     # 限制高度
            "tighten_spacing",   # 收紧间距
            "shrink_font",       # 缩小字号
            "disable_scroll"    # 禁用滚动
        ]
