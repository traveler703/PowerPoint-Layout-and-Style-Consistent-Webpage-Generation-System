<template>
  <div class="workspace-view active">
    <!-- Header -->
    <header class="workspace-header">
      <div class="workspace-header-left">
        <div class="logo">
          <div class="logo-icon">S</div>
          <span class="logo-text">PPT Studio</span>
        </div>
        <div class="workspace-stats">
          <div class="workspace-stat">
            <span class="workspace-stat-value">{{ store.templates.length }}</span>
            <span>个模板</span>
          </div>
        </div>
      </div>
      <div class="workspace-header-right">
        <button class="btn btn-ghost" @click="store.goToWorkspace()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          返回项目
        </button>
        <button class="btn btn-primary" @click="store.goToCreator()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          新建模板
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="workspace-main">
      <!-- Toolbar -->
      <div class="workspace-toolbar">
        <div class="toolbar-left">
          <div class="search-box">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input type="text" placeholder="搜索模板..." v-model="searchQuery">
          </div>
          <div class="filter-btn-group">
            <button
              class="filter-btn"
              :class="{ active: filterTag === '' }"
              @click="filterTag = ''"
            >全部</button>
            <button
              class="filter-btn"
              :class="{ active: filterTag === 'preset' }"
              @click="filterTag = 'preset'"
            >预设</button>
            <button
              class="filter-btn"
              :class="{ active: filterTag === 'user' }"
              @click="filterTag = 'user'"
            >用户自制</button>
          </div>
        </div>
        <div class="toolbar-right">
          <div class="view-toggle">
            <button class="view-toggle-btn" :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
              </svg>
            </button>
            <button class="view-toggle-btn" :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Templates Grid/List -->
      <div v-if="filteredTemplates.length > 0" class="projects-container" :class="viewMode === 'grid' ? 'projects-grid' : 'projects-list'">
        <div
          v-for="tpl in filteredTemplates"
          :key="tpl.template_id"
          class="project-card"
          :class="{ 'list-mode': viewMode === 'list' }"
          @click="previewTemplate(tpl)"
        >
          <div class="project-card-header">
            <div class="project-icon" :style="{ background: getTemplateBg(tpl) }">
              {{ getTemplateIcon(tpl) }}
            </div>
            <button class="project-menu-btn" @click.stop="showTemplateMenu($event, tpl)">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"/>
              </svg>
            </button>
          </div>
          <div class="project-preview" :style="{ background: getTemplateGradient(tpl) }">
            <div class="project-preview-text">{{ getTemplateIcon(tpl) }}</div>
          </div>
          <div class="project-name">{{ tpl.template_name }}</div>
          <div class="project-desc">{{ tpl.description }}</div>
          <div class="project-meta">
            <div class="project-meta-item" v-if="tpl.is_default">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
              </svg>
              默认
            </div>
            <div class="template-type-badge" :class="tpl.template_type === 'user' ? 'user' : 'preset'">
              {{ tpl.template_type === 'user' ? '用户自制' : '预设' }}
            </div>
            <div class="template-tags" style="margin-left: auto;">
              <span v-for="tag in (tpl.tags || []).slice(0, 3)" :key="tag" class="template-tag">{{ tag }}</span>
            </div>
          </div>
          <div class="template-colors">
            <div
              v-for="(color, idx) in getTemplateColors(tpl)"
              :key="idx"
              class="template-color"
              :style="{ background: color }"
            ></div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <div class="empty-state-icon">&#9733;</div>
        <h3>还没有模板</h3>
        <p>创建一个新模板，开始使用PPT Studio的模板管理功能。</p>
        <button class="btn btn-primary" @click="store.goToCreator()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          新建模板
        </button>
      </div>
    </main>

    <!-- Template Context Menu -->
    <div
      v-if="showMenu"
      class="context-menu"
      :style="{ top: menuPos.y + 'px', left: menuPos.x + 'px' }"
    >
      <div class="context-menu-item" @click="setAsDefault">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
        </svg>
        设为默认
      </div>
      <div class="context-menu-item" @click="editTemplate" v-if="selectedTemplate?.template_type === 'user'">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
        </svg>
        编辑模板
      </div>
      <div class="context-menu-item danger" @click="deleteTemplate" v-if="selectedTemplate?.template_type === 'user'">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
        </svg>
        删除模板
      </div>
    </div>

    <!-- Create Template Modal -->
    <div v-if="showCreateModal" class="modal-overlay active" @click.self="showCreateModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">新建模板</h3>
          <button class="modal-close" @click="showCreateModal = false">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">模板名称</label>
            <input class="form-input" v-model="newTemplate.name" placeholder="输入模板名称">
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <input class="form-input" v-model="newTemplate.description" placeholder="输入模板描述">
          </div>
          <div class="form-group">
            <label class="form-label">标签 (逗号分隔)</label>
            <input class="form-input" v-model="newTemplate.tags" placeholder="如: 科技, 商务">
          </div>
          <div class="form-group">
            <label class="form-label">主色调</label>
            <div class="color-picker-row">
              <input type="color" v-model="newTemplate.primaryColor" class="color-input">
              <input class="form-input" v-model="newTemplate.primaryColor" placeholder="#6366f1" style="flex:1">
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showCreateModal = false">取消</button>
          <button class="btn btn-primary" @click="createTemplate">创建</button>
        </div>
      </div>
    </div>

    <!-- Template Preview Modal -->
    <div v-if="previewingTemplate" class="modal-overlay active" @click.self="previewingTemplate = null">
      <div class="modal" style="max-width: 640px;">
        <div class="modal-header">
          <h3 class="modal-title">{{ previewingTemplate.template_name }}</h3>
          <button class="modal-close" @click="previewingTemplate = null">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="template-preview-large" :style="{ background: getTemplateGradient(previewingTemplate) }">
            <div class="template-preview-large-icon">{{ getTemplateIcon(previewingTemplate) }}</div>
            <div class="template-preview-large-title" :style="{ color: getTemplateTextColor(previewingTemplate) }">
              {{ previewingTemplate.template_name }}
            </div>
            <div class="template-preview-large-desc" :style="{ color: getTemplateSubtitleColor(previewingTemplate) }">
              {{ previewingTemplate.description }}
            </div>
          </div>
          <div class="template-detail-section">
            <div class="template-detail-label">标签</div>
            <div class="template-tags" style="margin-top: 8px;">
              <span v-for="tag in (previewingTemplate.tags || [])" :key="tag" class="template-tag">{{ tag }}</span>
            </div>
          </div>
          <div class="template-detail-section">
            <div class="template-detail-label">配色</div>
            <div class="template-colors" style="margin-top: 8px;">
              <div
                v-for="(color, idx) in getTemplateColors(previewingTemplate)"
                :key="idx"
                class="template-color"
                :style="{ background: color, width: '32px', height: '32px' }"
              ></div>
            </div>
          </div>
          <div v-if="Object.keys(previewingTemplate.css_variables || {}).length > 0" class="template-detail-section">
            <div class="template-detail-label">CSS 变量</div>
            <div class="template-css-vars">
              <div v-for="(val, key) in previewingTemplate.css_variables" :key="key" class="template-css-var">
                <span class="css-var-name">{{ key }}</span>
                <span class="css-var-val" :style="{ color: val }">{{ val }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="previewingTemplate = null">关闭</button>
          <button class="btn btn-primary" @click="useTemplate(previewingTemplate)">应用到项目</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { store } from '../stores/appStore'

const searchQuery = ref('')
const filterTag = ref('')
const viewMode = ref('grid')
const showMenu = ref(false)
const menuPos = ref({ x: 0, y: 0 })
const menuTemplate = ref(null)
const showCreateModal = ref(false)
const previewingTemplate = ref(null)

const newTemplate = ref({
  name: '',
  description: '',
  tags: '',
  primaryColor: '#6366f1'
})

const handleKeydown = (e) => {
  if (e.key === 'Escape') {
    showCreateModal.value = false
    previewingTemplate.value = null
  }
}

onMounted(async () => {
  await store.loadTemplates()
  document.addEventListener('click', closeMenu)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
  document.removeEventListener('keydown', handleKeydown)
})

const closeMenu = () => {
  showMenu.value = false
}

const filteredTemplates = computed(() => {
  let list = store.templates
  if (filterTag.value === 'preset') {
    list = list.filter(t => t.template_type !== 'user')
  } else if (filterTag.value === 'user') {
    list = list.filter(t => t.template_type === 'user')
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(t =>
      (t.template_name || '').toLowerCase().includes(q) ||
      (t.description || '').toLowerCase().includes(q) ||
      (t.tags || []).some(tag => tag.toLowerCase().includes(q))
    )
  }
  return list
})

function getTemplateIcon(template) {
  const tags = (template.tags || []).map(t => t.toLowerCase())
  if (tags.some(t => t.includes('科技') || t.includes('技术') || t.includes('赛博') || t.includes('cyber') || t.includes('tech'))) return '🚀'
  if (tags.some(t => t.includes('儿童') || t.includes('可爱') || t.includes('toy') || t.includes('活泼'))) return '🎨'
  if (tags.some(t => t.includes('商务') || t.includes('business'))) return '💼'
  if (tags.some(t => t.includes('学术') || t.includes('教育'))) return '📚'
  if (tags.some(t => t.includes('自然') || t.includes('环保'))) return '🌿'
  return '✨'
}

function getTemplateGradient(template) {
  const cssVars = template.css_variables || {}
  const primary = cssVars['color-primary'] || '#6366f1'
  const secondary = cssVars['color-secondary'] || '#8b5cf6'
  const bgColor = cssVars['color-background'] || cssVars['color-surface'] || '#ffffff'
  return isColorDark(bgColor)
    ? `linear-gradient(135deg, ${bgColor}, ${adjustBrightness(bgColor, 20)})`
    : `linear-gradient(135deg, ${primary}, ${secondary})`
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

function getTemplateBg(template) {
  const cssVars = template.css_variables || {}
  const primary = cssVars['color-primary'] || '#6366f1'
  return `rgba(${hexToRgb(primary)}, 0.15)`
}

function getTemplateColors(template) {
  const cssVars = template.css_variables || {}
  const keys = Object.keys(cssVars).filter(k => k.startsWith('color-accent-'))
  const accentColors = keys.map(k => cssVars[k]).filter(Boolean)
  return [
    cssVars['color-primary'] || '#6366f1',
    cssVars['color-secondary'] || '#8b5cf6',
    ...accentColors.slice(0, 3)
  ].slice(0, 4)
}

function isColorDark(color) {
  if (!color) return false
  color = color.replace('#', '')
  if (color.length === 3) color = color[0] + color[0] + color[1] + color[1] + color[2] + color[2]
  if (color.length !== 6) return false
  const r = parseInt(color.substring(0, 2), 16)
  const g = parseInt(color.substring(2, 4), 16)
  const b = parseInt(color.substring(4, 6), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 < 128
}

function adjustBrightness(hex, percent) {
  if (!hex) return '#333333'
  hex = hex.replace('#', '')
  if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2]
  if (hex.length !== 6) return '#333333'
  const num = parseInt(hex, 16)
  const amt = Math.round(2.55 * percent)
  const R = Math.min(255, Math.max(0, (num >> 16) + amt))
  const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amt))
  const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt))
  return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)
}

function hexToRgb(hex) {
  if (!hex) return '99, 102, 241'
  hex = hex.replace('#', '')
  if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2]
  if (hex.length !== 6) return '99, 102, 241'
  const r = parseInt(hex.substring(0, 2), 16)
  const g = parseInt(hex.substring(2, 4), 16)
  const b = parseInt(hex.substring(4, 6), 16)
  return `${r}, ${g}, ${b}`
}

function showTemplateMenu(event, template) {
  event.stopPropagation()
  menuTemplate.value = template
  menuPos.value = { x: event.clientX, y: event.clientY }
  showMenu.value = true
}

function setAsDefault() {
  showMenu.value = false
  store.setTemplateAsDefault(menuTemplate.value.template_id)
}

function editTemplate() {
  showMenu.value = false
  store.showToastMessage('编辑功能开发中')
}

function deleteTemplate() {
  showMenu.value = false
  store.deleteTemplate(menuTemplate.value.template_id)
}

function previewTemplate(template) {
  previewingTemplate.value = template
}

function useTemplate(template) {
  store.selectTemplate(template.template_id)
  previewingTemplate.value = null
  store.showToastMessage('已选择模板: ' + template.template_name)
  store.goToWorkspace()
}

async function createTemplate() {
  if (!newTemplate.value.name.trim()) {
    store.showToastMessage('请输入模板名称')
    return
  }
  const tags = newTemplate.value.tags.split(',').map(t => t.trim()).filter(Boolean)
  const cssVars = {
    'color-primary': newTemplate.value.primaryColor,
    'color-secondary': newTemplate.value.primaryColor
  }
  await store.createTemplate({
    template_name: newTemplate.value.name,
    description: newTemplate.value.description,
    tags: tags,
    css_variables: cssVars,
    template_type: 'user'
  })
  showCreateModal.value = false
  newTemplate.value = { name: '', description: '', tags: '', primaryColor: '#6366f1' }
}
</script>

<style scoped>
.filter-btn-group {
  display: flex;
  gap: 4px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 3px;
}

.filter-btn-group .filter-btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.15s;
}

.filter-btn-group .filter-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.filter-btn-group .filter-btn.active {
  background: var(--accent);
  color: white;
}

.template-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.template-tag {
  padding: 2px 8px;
  background: var(--bg-tertiary);
  color: var(--text-muted);
  border-radius: 4px;
  font-size: 11px;
}

.template-colors {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.template-color {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

/* Large preview modal */
.template-preview-large {
  height: 200px;
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.template-preview-large-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.template-preview-large-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}

.template-preview-large-desc {
  font-size: 14px;
}

.template-detail-section {
  margin-bottom: 16px;
}

.template-detail-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.template-css-vars {
  margin-top: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.template-css-var {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}

.template-css-var:last-child {
  border-bottom: none;
}

.css-var-name {
  color: var(--text-muted);
  font-family: monospace;
}

.css-var-val {
  font-family: monospace;
}

.color-picker-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.color-input {
  width: 48px;
  height: 42px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  padding: 2px;
  background: var(--bg-tertiary);
}

.template-type-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.template-type-badge.preset {
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
}

.template-type-badge.user {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}
</style>
