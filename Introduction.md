# 项目简介：PowerPoint 风格网页一致性生成系统

本项目的核心使命是开发一个基于大语言模型（LLM）的智能网页生成系统，将传统的 PowerPoint 演示文稿制作体验转化为高性能、跨平台的网页格式（HTML/Markdown）。系统通过“模板约束 + LLM 生成”的混合方案，解决传统 PPT 制作耗时、多页风格难统一以及跨平台分发受限的痛点。

## 1. 项目简介 (Project Introduction)

本项目的全称为 PowerPoint Layout-and-Style-Consistent Webpage Generation System（PPT 版式与风格一致的网页生成系统）。
该项目旨在解决传统 PPT 制作中排版耗时、多页视觉风格难以统一、以及跨平台分发受限的痛点。项目采用 “模板约束 + LLM 生成” 的混合方法，将 PPT 页面抽象为“版式 + 组件 + 视觉风格”的组合，利用大语言模型（LLM）的推理与代码生成能力，自动输出高设计质量、全球一致性强的 HTML 或 Markdown 格式的网页演示文稿。

## 2. 功能模块、组件及其作用 (Functional Modules & Components)

项目构建了一个完整的自动化生成管线，包含以下核心模块：

- 内容输入模块 (Content Input Module)：接收并结构化处理用户输入的页面信息（如多级标题、正文、列表、图片 URL、表格等），识别语义层级，为下游模块提供标准输入。

- 结构化可重用表示框架 (Structured Reusable Representation Framework)：

    - 版式原子库 (Layout Atom Library)：预设的最小布局单元集合。

    - 组件规格 (Component Specifications)：标准化的 UI 组件定义（尺寸、间距等元数据）。

    - 风格令牌 (Style Tokens)：控制颜色、字体、间距等视觉属性的变量系统，是确保跨页风格一致性的核心组件。

- 自动化版式选型与推理引擎 (Reasoning Engine)：根据内容的语义特征（如要点数量、文本长度、是否有图表等），通过约束求解或 LLM 推理，自动从原子库中匹配最优版式。

- 基于 LLM 的代码生成模块 (LLM-based Code Generation)：利用 System Prompt 设计与风格令牌注入技术，调用 LLM 生成符合 W3C 标准的 HTML 或语义化的 Markdown 代码。

- 预览与编辑模块 (Preview & Edit Module)：提供“所见即所得”的实时预览，支持用户通过自然语言指令（如“把标题调大”）或直接拖拽等方式对生成结果进行二次调整。

- 量化评估模块 (Quantitative Evaluation Framework)：建立自动化评估体系，计算元素重叠率（需为 0）和全局颜色偏差（需 ≤5%），为系统优化提供反馈信号。

## 3. 用户工作流程与预期效果 (Workflow & Expected Results)

从用户角度看，项目实现的工作流程如下：

1. 输入内容：用户上传文档或键入结构化内容。

2. 选择风格：用户从预设模板（如商务蓝、学术灰）中选择或自定义风格令牌。

3. 智能生成：系统自动完成语义分析、版式匹配、风格注入并一键生成多页演示网页。

4. 预览修改：用户查看缩略图或放大单页，通过自然语言或手动编辑微调。

5. 导出分发：一键导出为 HTML 单文件或复制 Markdown 代码用于分发。

预期实现效果：

- 效率提升：相比传统手动排版，视觉布局时间减少 50% 以上。

- 设计质量：实现 0 元素重叠，确保页面布局的理性与美观。

- 视觉一致性：多页间的全局颜色偏差控制在 5% 以内。

- 极简体验：新用户可在 10 分钟内完成首个作品制作，核心流程不超过 5 步操作。

4. 其他重要内容 (Other Crucial Information)

技术栈约束：

- 前端：Vue 3.x。

- 后端：Python FastAPI。

- AI 框架：LangChain/LangGraph。

- 数据库：MySQL/Redis。

- 输出限制：本项目不支持传统的 .pptx 格式生成，仅专注于 Web 兼容格式。