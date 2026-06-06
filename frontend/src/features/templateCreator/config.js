import { PAGE_TYPES } from '@/constants/pageTypes'

export const FIXED_PREVIEW_OUTLINE = Object.freeze([
  {
    page_type: PAGE_TYPES.COVER,
    title: '产品战略发布会',
    subtitle: '创新驱动增长',
    date_badge: '2026年6月'
  },
  {
    page_type: PAGE_TYPES.TOC,
    title: '目录',
    bullets: [
      '第一章 市场趋势与机遇',
      '第二章 核心产品矩阵',
      '第三章 技术架构升级',
      '第四章 战略规划与展望'
    ]
  },
  {
    page_type: PAGE_TYPES.SECTION,
    title: '第一章',
    subtitle: '市场趋势与机遇'
  },
  {
    page_type: PAGE_TYPES.CONTENT,
    title: '行业现状分析',
    bullets: [
      '全球数字化转型加速，AI技术深入各行各业',
      '2026年全球企业级SaaS市场规模预计突破3000亿美元',
      'AI Agent技术成为企业效率提升的关键驱动力',
      '数据安全与隐私合规需求持续增长'
    ]
  },
  {
    page_type: PAGE_TYPES.SECTION,
    title: '第二章',
    subtitle: '核心产品矩阵'
  },
  {
    page_type: PAGE_TYPES.CONTENT,
    title: '产品体系概览',
    bullets: [
      'SmartChat：新一代企业级AI对话平台',
      'DataPilot：智能数据分析与可视化工具',
      'FlowMaster：低代码业务流程自动化引擎',
      '三款产品深度集成，形成完整解决方案'
    ]
  },
  {
    page_type: PAGE_TYPES.ENDING,
    title: '谢谢观看',
    subtitle: '期待与您携手共创未来'
  }
])

export const COLOR_PRESETS = Object.freeze([
  {
    name: '赛博朋克',
    colors: ['#00ffff', '#0088ff', '#a855f7', '#ec4899'],
    vars: {
      'color-primary': '#00ffff',
      'color-secondary': '#0088ff',
      'color-accent-cyan': '#00ffff',
      'color-accent-blue': '#0088ff',
      'color-accent-purple': '#a855f7',
      'color-accent-pink': '#ec4899',
      'color-background': '#0a0c14',
      'color-surface': '#1a2035',
      'color-text': '#e0e0e0',
      'color-card': '#151a2d'
    }
  },
  {
    name: '水墨风',
    colors: ['#1a1a1a', '#8B7355', '#C54B4B', '#F5F0E8'],
    vars: {
      'color-primary': '#1a1a1a',
      'color-secondary': '#8B7355',
      'color-accent-seal': '#C54B4B',
      'color-background': '#F5F0E8',
      'color-surface': '#FDFBF7',
      'color-text': '#2d2d2d',
      'color-card': '#FFFFFF'
    }
  },
  {
    name: '商务蓝',
    colors: ['#1e3a5f', '#2c5282', '#3182ce', '#63b3ed'],
    vars: {
      'color-primary': '#1e3a5f',
      'color-secondary': '#2c5282',
      'color-accent-blue': '#3182ce',
      'color-accent-light': '#63b3ed',
      'color-background': '#f7fafc',
      'color-surface': '#ffffff',
      'color-text': '#1a202c',
      'color-card': '#ffffff'
    }
  },
  {
    name: '清新绿',
    colors: ['#166534', '#15803d', '#22c55e', '#86efac'],
    vars: {
      'color-primary': '#166534',
      'color-secondary': '#15803d',
      'color-accent-green': '#22c55e',
      'color-accent-light': '#86efac',
      'color-background': '#f0fdf4',
      'color-surface': '#ffffff',
      'color-text': '#14532d',
      'color-card': '#ffffff'
    }
  },
  {
    name: '暖橙',
    colors: ['#9a3412', '#c2410c', '#ea580c', '#fdba74'],
    vars: {
      'color-primary': '#9a3412',
      'color-secondary': '#c2410c',
      'color-accent-orange': '#ea580c',
      'color-accent-light': '#fdba74',
      'color-background': '#fff7ed',
      'color-surface': '#ffffff',
      'color-text': '#431407',
      'color-card': '#ffffff'
    }
  }
])

export function createDefaultTemplateConfig() {
  return {
    template_id: `my_template_${Date.now().toString(36)}`,
    template_name: '我的自定义模板',
    description: '使用 AI 模板创建器生成的模板',
    version: '1.0.0',
    css_variables: {
      'color-primary': '#6366f1',
      'color-secondary': '#8b5cf6',
      'color-background': '#ffffff',
      'color-surface': '#f8fafc',
      'color-text': '#1e293b',
      'color-text-muted': '#64748b',
      'color-card': '#ffffff',
      'font-body': "'Segoe UI', 'Microsoft YaHei', sans-serif",
      'font-heading': "'Segoe UI', 'Microsoft YaHei', sans-serif"
    },
    page_types: {
      [PAGE_TYPES.COVER]: {
        skeleton: '<div class="slide cover"><h1 class="main-title">{{title}}</h1><p class="subtitle">{{subtitle}}</p></div>',
        placeholders: ['title', 'subtitle']
      },
      [PAGE_TYPES.CONTENT]: {
        skeleton: '<div class="slide content"><h2 class="page-title">{{title}}</h2><div class="page-content">{{content}}</div></div>',
        placeholders: ['title', 'content']
      },
      [PAGE_TYPES.TOC]: {
        skeleton: '<div class="slide toc"><h2 class="page-title">{{title}}</h2><div class="toc-list">{{toc_items}}</div></div>',
        placeholders: ['title', 'toc_items']
      },
      [PAGE_TYPES.ENDING]: {
        skeleton: '<div class="slide ending"><h1>{{title}}</h1><p>{{message}}</p></div>',
        placeholders: ['title', 'message']
      }
    },
    raw_html: '',
    viewport: { width: 1280, height: 720 },
    tags: [],
    template_type: 'user'
  }
}
