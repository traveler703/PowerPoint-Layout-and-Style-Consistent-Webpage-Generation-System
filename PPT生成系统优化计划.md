# PPT 生成系统优化计划

> 规划日期: 2026-05-02
> 目标: 分步骤优化 LLM 提示词系统，每个步骤独立创建新文件而非修改原版，便于对比验证

---

## 当前系统分析

### 核心流程概览

```
用户文本/大纲
    ↓
Step 1: 文档解析 (document_parsing.py) → LLM 1次
    ↓
Step 2: 构建大纲 (PresentationOutline)
    ↓
Step 3: 加载模板 (template_loader.py)
    ↓
Step 4: 渲染固定页面 (cover/toc/section/ending) → 无LLM
    ↓
Step 5: 内容页面生成
    ├── Stage 1: 布局分析 (layout_analysis.py) → 每页1次LLM
    └── Stage 2: HTML生成 (content_html.py) → 每页1次LLM
    ↓
Step 6: 合并页面 → 输出HTML
```

### 当前问题清单

| 问题 | 严重度 | 描述 |
|------|--------|------|
| **Prompts过长** | 高 | system prompt 包含所有布局类型、所有规则，每次调用重复发送大量上下文 |
| **无Few-shot示例** | 高 | LLM只能靠推理，没有示例参考，质量不稳定 |
| **语义脱节** | 高 | CSS变量(`color-primary`)和语义概念(`accent`)没有映射，LLM无法理解设计意图 |
| **布局选择粗粒度** | 中 | layout_analysis只返回类型名，不返回具体约束，Stage2凭空发挥 |
| **HTML解析脆弱** | 中 | `parse_html_response`只是粗暴截取html标签，缺少结构化验证 |
| **无自纠正机制** | 中 | HTML生成失败后没有重试/修复流程 |
| **无质量评分** | 中 | 生成后没有质量评估，无法对比优化效果 |
| **页面间无关联感知** | 低 | 每页独立生成，section内的页面应该风格一致 |
| **提示词分散耦合** | 低 | prompts逻辑分散在各处，难以系统优化 |

---

## 分步优化计划

每个步骤：创建 `*_v2.py` 新文件，不修改原版本，对比运行效果。

---

### Step 1: 建立新的 Prompt 基础设施

**目标**: 把分散在多个文件的 prompts 逻辑统一管理，加入 few-shot 示例系统

**新建文件**:
- `generator/prompts/prompt_registry.py` — Prompt总注册表
- `generator/prompts/examples.py` — 各类型页面的 few-shot 示例库
- `generator/prompts/examples_data.py` — 示例原始数据

**核心改动**:

1. **PromptRegistry 类** — 统一管理所有 prompt 的构建

```python
class PromptRegistry:
    def build(self, step: PromptStep, page_type: str, context: dict) -> tuple[str, str]:
        # 动态拼接 system + user prompt
        # 自动注入 relevant examples
```

2. **Few-shot 示例系统** — 每个页面类型都有 1-2 个代表性示例

```python
# 覆盖页示例
cover_example = Example(
    page_type="cover",
    input=SemanticPageInput(...),
    layout_analysis_output={...},
    html_output="<div class=\"slide cover\">...</div>"
)

# 内容页示例 (按布局类型分类)
timeline_example = Example(
    layout_type="timeline",
    input=SemanticPageInput(...),
    html_output="<div class=\"slide content\">...</div>"
)
```

3. **动态 prompt 长度控制** — 根据页面类型和内容复杂度，动态决定 prompt 长度

**对比价值**: 评估 few-shot 对生成质量的提升幅度

---

### Step 2: 语义化 CSS 变量映射 + 增强版 Layout Analysis

**目标**: 让 LLM 理解设计语义的映射关系，输出更结构化的布局约束

**新建文件**:
- `generator/prompts/semantic_css.py` — CSS变量 → 语义概念映射表
- `generator/prompts/layout_analysis_v2.py` — 增强版布局分析

**核心改动**:

1. **语义映射表** — 定义每套模板的语义角色

```python
# tech.json 的语义映射
TECH_SEMANTIC_MAP = {
    "color-primary": "main_accent",       # 主强调色
    "color-secondary": "secondary_accent", # 辅助强调色
    "color-background": "page_bg",         # 页面背景
    "color-surface": "card_bg",           # 卡片/区块背景
    "color-text": "body_text",            # 正文文字
    "color-text-secondary": "caption",    # 辅助说明文字
    "color-border": "dividers",           # 分割线/边框
    "font-heading": "display_font",      # 大标题字体
    "font-body": "body_font",            # 正文字体
}

# toy.json 的语义映射
TOY_SEMANTIC_MAP = {
    "color-primary": "playful_accent",
    "color-background": "warm_bg",
    ...
}
```

2. **增强版 Layout Analysis 输出** — 不仅返回类型，还返回具体结构约束

```python
# 原版输出:
{"layout_type": "timeline", "design_suggestions": "..."}

# v2 输出:
{
    "layout_type": "timeline",
    "structure": {
        "orientation": "horizontal",      # 时间线方向
        "nodes_count": 4,               # 节点数量
        "has_connector_line": True,      # 是否有连接线
        "has_icons": False,             # 是否需要图标
    },
    "component_zones": [
        {"id": "header", "height": 60, "content": "页面标题"},
        {"id": "timeline_container", "width": 1100, "height": 350,
         "x": 60, "y": 160, "items_per_row": 4},
    ],
    "color_usage": {
        "node_circles": "main_accent",
        "connector_lines": "secondary_accent",
        "labels": "body_text"
    },
    "typography": {
        "title": {"font": "display_font", "size": 36},
        "node_labels": {"font": "body_font", "size": 16},
    },
    "design_notes": "..."
}
```

3. **布局选择智能推荐** — 基于内容结构自动推荐布局

```python
def recommend_layout(page: SemanticPageInput) -> list[str]:
    """根据内容特征推荐最合适的布局类型"""
    if len(page.timeline_items) >= 3 and "演变" in page.summary:
        return ["timeline", "stepped"]
    if len(page.bullet_points) <= 4 and all(isinstance(b, dict) for b in page.bullet_points):
        return ["card_grid", "dashboard"]
    if page.has_chart:
        return ["dashboard", "split_columns"]
    ...
```

**对比价值**: 评估语义映射 + 结构化约束对HTML生成准确性的提升

---

### Step 3: 增强版 HTML 生成 Prompt

**目标**: 基于 Step 2 的结构化约束，生成更精确的 HTML

**新建文件**:
- `generator/prompts/content_html_v2.py` — 增强版HTML生成
- `generator/prompts/html_validator.py` — HTML结构验证器

**核心改动**:

1. **强化的 System Prompt** — 包含设计规则 + 示例 + 约束条件

```python
# content_html_v2.py
def build_html_generation_prompt_v2(
    page: SemanticPageInput,
    layout_result: LayoutAnalysisV2,  # 来自Step2的增强结果
    semantic_map: SemanticMap,
    css_vars: dict,
    examples: list[Example]
) -> tuple[str, str]:

    system = f"""你是专业的HTML幻灯片生成专家。

## 设计语义参考
{semantic_map.to_llm_description()}

## 当前页面约束
{layout_result.to_structured_constraints()}

## 内容详情
- 标题: {page.title}
- 要点数量: {len(page.bullet_points)}
- 布局类型: {layout_result.layout_type}

## 关键规则
1. 画布: 1280x720, 内容区: 1160x530 (x=60, y=130)
2. 使用flex/grid布局，禁止position: absolute
3. 颜色必须使用: {list(semantic_map.color_bindings.keys())}
4. 字体: {semantic_map.font_bindings}

## 示例参考
{examples.render_for_prompt()}
"""
```

2. **HTML 验证器** — 生成后自动检查结构

```python
class HtmlValidator:
    def validate(self, html: str, constraints: LayoutConstraints) -> ValidationResult:
        checks = [
            self._check_no_absolute_positioning(html),
            self._check_no_overflow_visible(html),
            self._check_dimensions_valid(html),
            self._check_colors_from_palette(html, palette),
            self._check_text_fit_in_zones(html, constraints),
            self._check_no_forbidden_tags(html),
        ]
        return ValidationResult(passed=all(c.passed for c in checks),
                                 issues=[c for c in checks if not c.passed])
```

**对比价值**: 对比 v1 和 v2 的 HTML 生成质量

---

### Step 4: 新的 LLM 客户端 + 重试策略

**目标**: 更强的错误处理和自适应重试

**新建文件**:
- `generator/llm_client_v2.py` — 增强版LLM客户端
- `generator/llm_config.py` — LLM调用配置管理

**核心改动**:

1. **多模型支持** — 支持 DeepSeek + OpenAI 双模型对比

```python
class LLMClientV2:
    def __init__(self, primary: str = "deepseek", fallback: str = "openai"):
        self.primary = self._create_client(primary)
        self.fallback = self._create_client(fallback)

    async def complete(self, system: str, user: str,
                       attempt: int = 1) -> str:
        try:
            return await self.primary.complete(system, user)
        except RateLimitError:
            if attempt < self.max_retries:
                await self._backoff(attempt)
                return await self.complete(system, user, attempt + 1)
        except APIError as e:
            # 切换到备用模型
            return await self.fallback.complete(system, user)
```

2. **Token 用量追踪** — 记录每次调用的 token 消耗

```python
@dataclass
class LLMCallRecord:
    step: str
    page_index: int
    input_tokens: int
    output_tokens: int
    model: str
    latency_ms: float
    success: bool
```

3. **Prompt 版本标记** — 便于 A/B 对比

```python
class PromptVersion:
    PROMPT_V1 = "original"
    PROMPT_V2 = "enhanced_with_examples"
    PROMPT_V3 = "semantic_mapping"
```

**对比价值**: 评估不同模型、不同提示词版本的效果差异

---

### Step 5: 集成测试 + 质量评分系统

**目标**: 系统性地对比原版和优化版的输出质量

**新建文件**:
- `test_step1_prompts.py` — 测试 prompt registry
- `test_step2_layout_v2.py` — 测试增强版布局分析
- `test_step3_html_v2.py` — 测试增强版HTML生成
- `test_step4_llm_v2.py` — 测试LLM客户端v2
- `test_step5_integration.py` — 端到端集成测试
- `evaluator/quality_scorer.py` — 质量评分系统

**核心改动**:

1. **质量评分体系** — 多维度评分

```python
@dataclass
class QualityScore:
    layout_accuracy: float      # 布局是否按约束生成
    color_adherence: float      # 颜色是否遵循设计系统
    typography_consistency: float # 字体字号一致性
    content_completeness: float  # 内容是否完整呈现
    visual_balance: float        # 视觉平衡感
    total: float

    def grade(self) -> str:
        if self.total >= 0.9: return "A"
        if self.total >= 0.8: return "B"
        if self.total >= 0.7: return "C"
        return "D"
```

2. **Side-by-side 对比报告** — 自动生成对比HTML

```python
def generate_comparison_report(v1_html: str, v2_html: str,
                                v1_score: QualityScore,
                                v2_score: QualityScore) -> str:
    """生成可视化对比报告"""
```

3. **Prompt 效率分析** — Token 消耗对比

```python
@dataclass
class PromptEfficiency:
    version: str
    avg_input_tokens: float
    avg_output_tokens: float
    avg_generation_time_ms: float
    success_rate: float
    quality_score: QualityScore
```

**对比价值**: 量化展示每个优化步骤的实际收益

---

### Step 6: 端到端编排 + 并行优化

**目标**: 将所有优化整合为新的生成管道

**新建文件**:
- `pipeline_v2.py` — 新的生成管道
- `run_v2_comparison.py` — 原版 vs 优化版对比脚本
- `run_v2_full.py` — 纯优化版生成脚本

**核心改动**:

1. **新管道架构**

```python
class PresentationGeneratorV2:
    def __init__(self):
        self.prompt_registry = PromptRegistry()
        self.llm_client = LLMClientV2()
        self.semantic_css = SemanticCSS()
        self.html_validator = HtmlValidator()
        self.quality_scorer = QualityScorer()

    async def generate(self, outline: PresentationOutline,
                       template: str, version: str = "v2") -> GenerationResultV2:
        # Step 1: 解析文档 (如需要)
        # Step 2: 加载模板 + 语义映射
        # Step 3: 渲染固定页面
        # Step 4: 内容页面生成 (Step 2+3 流水线)
        # Step 5: HTML验证 + 自纠正
        # Step 6: 质量评分 + 报告生成
```

2. **流水线式布局→HTML生成** — 不再是串行的两次LLM调用

```python
async def generate_content_page(self, page: SemanticPageInput) -> str:
    # 并行构建 layout 和 html prompts
    layout_task = self.prompt_registry.build("layout", page.page_type, ...)
    html_task = self.prompt_registry.build("html", page.page_type, ...)

    # 如果 layout 结果可以复用(如section内风格一致)，跳过layout调用
    if self._can_reuse_layout(page, self.last_layout):
        layout_result = self.last_layout
    else:
        layout_result = await self.llm_client.complete(*layout_task)
        self.last_layout = layout_result

    # HTML生成
    html_result = await self.llm_client.complete(
        *self.prompt_registry.build("html", page, layout_result, ...)
    )

    # 验证
    validation = self.html_validator.validate(html_result, layout_result)
    if not validation.passed:
        # 自纠正
        html_result = await self._self_correct(html_result, validation.issues)

    return html_result
```

3. **章节内风格一致性** — 同一section的页面共享布局策略

```python
# 分析section内的内容模式
section_patterns = self._analyze_section_pattern(section)
for i, page in enumerate(section.content_pages):
    if i == 0:
        # 第一个页面完整走两阶段
        layout = await self.generate_layout(page)
    else:
        # 后续页面复用或微调
        layout = self._adapt_layout(self.last_layout, page)
```

**对比价值**: 完整对比原管道和新管道的输出质量和效率

---

### Step 7: 元提示词工程 (Meta-Prompting)

**目标**: 用LLM自动优化提示词本身

**新建文件**:
- `generator/prompts/meta_prompter.py` — 元提示词系统
- `generator/prompts/optimizer.py` — 提示词自动优化器

**核心改动**:

```python
class PromptOptimizer:
    """用LLM分析和优化提示词"""

    async def analyze_failures(self, failed_cases: list[FailureCase]) -> str:
        """分析批量失败案例，找出提示词共性缺陷"""

    async def suggest_improvements(self, current_prompt: str,
                                   analysis: str) -> str:
        """基于分析提出具体改进建议"""

    async def generate_variants(self, prompt: str, count: int = 3) -> list[str]:
        """生成多个变体进行A/B测试"""
```

---

## 实施顺序与依赖关系

```
Phase 1 (基础设施)
├── Step 1: Prompt Registry + Few-shot Examples
└── Step 4: LLM Client V2 + Retry
         │
         ▼
Phase 2 (核心优化)
├── Step 2: 语义CSS映射 + Layout V2
└── Step 3: HTML生成 Prompt V2 + Validator
         │
         ▼
Phase 3 (集成验证)
├── Step 5: 测试 + 质量评分
└── Step 6: 端到端管道 V2
         │
         ▼
Phase 4 (自动优化)
└── Step 7: Meta-Prompting
```

## 预期收益

| 优化项 | 预期提升 |
|--------|----------|
| Few-shot 示例 | HTML结构准确性 +15-25% |
| 语义CSS映射 | 颜色一致性 +20-30% |
| 结构化布局约束 | 布局准确性 +20-30% |
| HTML验证+自纠正 | 生成成功率 +10-15% |
| 章节内风格一致 | 整体视觉连贯性 +15-20% |
| Prompt Registry | 开发效率 +30% (可快速切换对比) |
| Token优化 | 每次调用节省 ~500-1000 tokens |

---

## 文件清单

| 步骤 | 新建文件 | 依赖 |
|------|----------|------|
| Step 1 | `generator/prompts/examples.py` | 无 |
| Step 1 | `generator/prompts/examples_data.py` | 无 |
| Step 1 | `generator/prompts/prompt_registry.py` | Step 1 |
| Step 2 | `generator/prompts/semantic_css.py` | 无 |
| Step 2 | `generator/prompts/layout_analysis_v2.py` | Step 1, Step 2 |
| Step 3 | `generator/prompts/html_validator.py` | 无 |
| Step 3 | `generator/prompts/content_html_v2.py` | Step 1, 2, 3 |
| Step 4 | `generator/llm_config.py` | 无 |
| Step 4 | `generator/llm_client_v2.py` | Step 4 |
| Step 5 | `evaluator/quality_scorer.py` | 无 |
| Step 5 | `test_step1_prompts.py` | Step 1 |
| Step 5 | `test_step2_layout_v2.py` | Step 2 |
| Step 5 | `test_step3_html_v2.py` | Step 3 |
| Step 5 | `test_step4_llm_v2.py` | Step 4 |
| Step 5 | `test_step5_integration.py` | Step 1-4 |
| Step 6 | `pipeline_v2.py` | Step 1-5 |
| Step 6 | `run_v2_comparison.py` | Step 1-5 |
| Step 6 | `run_v2_full.py` | Step 1-5 |
| Step 7 | `generator/prompts/meta_prompter.py` | Step 1-3 |
| Step 7 | `generator/prompts/optimizer.py` | Step 7 |
