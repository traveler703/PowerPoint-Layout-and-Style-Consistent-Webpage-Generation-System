export const PAGE_TYPES = Object.freeze({
  COVER: 'cover',
  CONTENT: 'content',
  TOC: 'toc',
  SECTION: 'section',
  ENDING: 'ending',
  COMPARE: 'compare',
  CHART: 'chart',
  TIMELINE: 'timeline',
  QA: 'qa'
})

const PAGE_TYPE_ALIASES = Object.freeze({
  title: PAGE_TYPES.COVER,
  end: PAGE_TYPES.ENDING
})

export function normalizePageType(value, fallback = PAGE_TYPES.CONTENT) {
  const normalized = String(value || '').trim().toLowerCase()
  return PAGE_TYPE_ALIASES[normalized] || normalized || fallback
}

export function getPageType(page, fallback = PAGE_TYPES.CONTENT) {
  return normalizePageType(
    page?.page_type || page?.slide_type || page?.type || page?.layout,
    fallback
  )
}

export const PAGE_TYPE_LABELS = Object.freeze({
  [PAGE_TYPES.COVER]: '封面页',
  [PAGE_TYPES.TOC]: '目录页',
  [PAGE_TYPES.SECTION]: '章节页',
  [PAGE_TYPES.CONTENT]: '内容页',
  [PAGE_TYPES.ENDING]: '结束页',
  [PAGE_TYPES.COMPARE]: '对比页',
  [PAGE_TYPES.CHART]: '图表页',
  [PAGE_TYPES.TIMELINE]: '时间轴',
  [PAGE_TYPES.QA]: '问答页'
})

export const PAGE_TYPE_ICONS = Object.freeze({
  [PAGE_TYPES.COVER]: '📄',
  [PAGE_TYPES.TOC]: '📋',
  [PAGE_TYPES.SECTION]: '🏷️',
  [PAGE_TYPES.CONTENT]: '📝',
  [PAGE_TYPES.ENDING]: '🏁',
  [PAGE_TYPES.COMPARE]: '⚖️',
  [PAGE_TYPES.CHART]: '📊',
  [PAGE_TYPES.TIMELINE]: '📅',
  [PAGE_TYPES.QA]: '❓'
})
