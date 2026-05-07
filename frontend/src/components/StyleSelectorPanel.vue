<template>
  <div class="template-grid">
    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
      <span>加载模板中...</span>
    </div>
    <div
      v-else
      v-for="template in store.templates"
      :key="template.template_id"
      class="template-card"
      :class="{ selected: store.selectedTemplate === template.template_id }"
      @click="selectTemplate(template.template_id)"
    >
      <div class="template-preview" :style="{ background: getTemplateGradient(template) }">
        <div class="template-preview-content">
          <div class="template-preview-icon">{{ getTemplateIcon(template) }}</div>
          <div class="template-preview-title" :style="{ color: getTemplateTextColor(template) }">
            {{ template.template_name }}
          </div>
          <div class="template-preview-subtitle" :style="{ color: getTemplateSubtitleColor(template) }">
            {{ template.tags?.join(' · ') || '' }}
          </div>
        </div>
        <div v-if="template.is_default" class="default-badge">默认</div>
      </div>
      <div class="template-info">
        <div class="template-name">{{ template.template_name }}</div>
        <div class="template-desc">{{ template.description }}</div>
        <div class="template-colors">
          <div
            v-for="(color, index) in getTemplateColors(template)"
            :key="index"
            class="template-color"
            :style="{ background: color }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { store } from '../stores/appStore'

const loading = ref(true)

// 初始化时加载模板
onMounted(async () => {
  await loadTemplates()
})

async function loadTemplates() {
  loading.value = true
  await store.loadTemplates()
  loading.value = false
}

const selectTemplate = (templateId) => {
  store.selectTemplate(templateId)
}

// 根据模板类型获取渐变背景
function getTemplateGradient(template) {
  const cssVars = template.css_variables || {}
  const primary = cssVars['color-primary'] || '#6366f1'
  const secondary = cssVars['color-secondary'] || '#8b5cf6'

  // 检测是否为深色主题
  const bgColor = cssVars['color-background'] || cssVars['color-surface'] || '#ffffff'
  const isDark = isColorDark(bgColor)

  if (isDark) {
    return `linear-gradient(135deg, ${bgColor}, ${adjustBrightness(bgColor, 20)})`
  }
  return `linear-gradient(135deg, ${primary}, ${secondary})`
}

function getTemplateTextColor(template) {
  const cssVars = template.css_variables || {}
  const bgColor = cssVars['color-background'] || cssVars['color-surface'] || '#ffffff'
  return isColorDark(bgColor) ? '#ffffff' : cssVars['color-text'] || '#1a1a1a'
}

function getTemplateSubtitleColor(template) {
  const cssVars = template.css_variables || {}
  const bgColor = cssVars['color-background'] || cssVars['color-surface'] || '#ffffff'
  return isColorDark(bgColor) ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.6)'
}

function getTemplateColors(template) {
  const cssVars = template.css_variables || {}
  return [
    cssVars['color-primary'] || '#6366f1',
    cssVars['color-secondary'] || '#8b5cf6',
    cssVars['color-accent-cyan'] || cssVars['color-accent-blue'] || cssVars['color-accent-red'] || cssVars['color-accent-green'] || cssVars['color-accent-purple'] || '#a855f7'
  ].filter(Boolean)
}

function getTemplateIcon(template) {
  const tags = (template.tags || []).map(t => t.toLowerCase())
  if (tags.some(t => t.includes('科技') || t.includes('技术') || t.includes('赛博') || t.includes('cyber') || t.includes('tech'))) {
    return '🚀'
  }
  if (tags.some(t => t.includes('儿童') || t.includes('可爱') || t.includes('toy') || t.includes('活泼'))) {
    return '🎨'
  }
  if (tags.some(t => t.includes('商务') || t.includes('business'))) {
    return '💼'
  }
  if (tags.some(t => t.includes('学术') || t.includes('学术'))) {
    return '📚'
  }
  if (tags.some(t => t.includes('自然') || t.includes('环保'))) {
    return '🌿'
  }
  return '✨'
}

// 判断颜色是否为深色
function isColorDark(color) {
  if (!color) return false
  // 移除 # 前缀
  color = color.replace('#', '')

  // 处理简写形式
  if (color.length === 3) {
    color = color[0] + color[0] + color[1] + color[1] + color[2] + color[2]
  }

  if (color.length !== 6) return false

  const r = parseInt(color.substring(0, 2), 16)
  const g = parseInt(color.substring(2, 4), 16)
  const b = parseInt(color.substring(4, 6), 16)

  // 计算亮度
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  return brightness < 128
}

// 调整颜色亮度
function adjustBrightness(hex, percent) {
  if (!hex) return '#333333'
  hex = hex.replace('#', '')

  if (hex.length === 3) {
    hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2]
  }

  if (hex.length !== 6) return '#333333'

  const num = parseInt(hex, 16)
  const amt = Math.round(2.55 * percent)
  const R = Math.min(255, Math.max(0, (num >> 16) + amt))
  const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amt))
  const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt))

  return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)
}
</script>

<style scoped>
.template-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  padding: 8px;
}

.loading-state {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #6b7280;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.template-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.template-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.template-card.selected {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2), 0 4px 12px rgba(0, 0, 0, 0.15);
}

.template-preview {
  height: 120px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.template-preview-content {
  text-align: center;
  padding: 16px;
}

.template-preview-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.template-preview-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.template-preview-subtitle {
  font-size: 12px;
}

.default-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(255, 255, 255, 0.9);
  color: #6366f1;
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
}

.template-info {
  padding: 12px;
  background: #f9fafb;
}

.template-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.template-desc {
  font-size: 11px;
  color: #6b7280;
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.template-colors {
  display: flex;
  gap: 4px;
}

.template-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
</style>
