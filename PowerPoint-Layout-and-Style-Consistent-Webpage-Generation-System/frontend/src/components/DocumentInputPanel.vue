<template>
  <div class="document-input-area">
    <!-- Input Panel -->
    <div class="input-panel">
      <div class="input-panel-header">
        <span class="input-panel-title">文档输入</span>
        <div class="input-tabs">
          <button class="input-tab" :class="{ active: store.inputMode === 'paste' }" @click="store.setInputMode('paste')">粘贴文本</button>
          <button class="input-tab" :class="{ active: store.inputMode === 'upload' }" @click="store.setInputMode('upload')">上传文件</button>
        </div>
      </div>
      <div class="input-panel-body">
        <!-- Text Input -->
        <div class="text-input-area" v-show="store.inputMode === 'paste'">
          <textarea
            v-model="store.documentText"
            @input="updateCharCount"
            :disabled="store.isParsing"
            placeholder="在此粘贴您的文档内容...

支持格式：
• Markdown 文档
• Word 文档 (.docx)
• PDF 文档
• 纯文本

粘贴后点击「开始解析」按钮，系统将自动分析内容结构并生成PPT大纲。"
          ></textarea>
        </div>
        <!-- File Upload -->
        <div class="file-upload-area" v-show="store.inputMode === 'upload'" @dragover.prevent="handleDragOver" @dragleave="handleDragLeave" @drop.prevent="handleDrop" @click="triggerFileInput">
          <div class="drop-zone" :class="{ dragover: isDragOver }">
            <div class="drop-zone-icon">📄</div>
            <div class="drop-zone-text">将文件拖拽到此处，或<span>点击选择文件</span></div>
            <div class="drop-zone-formats">支持 .md .docx .pdf .txt 格式</div>
          </div>
          <input type="file" ref="fileInputRef" id="fileInput" accept=".md,.docx,.pdf,.txt" style="display: none;" @change="handleFileSelect">
        </div>
      </div>
      <div class="input-panel-footer">
        <span class="input-hint">{{ store.charCount }} 字</span>
        <button 
          class="btn btn-primary" 
          @click="handleParse"
          :disabled="store.isParsing || !store.documentText.trim()"
        >
          <span v-if="store.isParsing" class="loading-spinner"></span>
          <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
          {{ store.isParsing ? '解析中...' : '开始解析' }}
        </button>
      </div>
    </div>

    <!-- Parsed Panel -->
    <div class="parsed-panel">
      <div class="parsed-panel-header">
        <span class="input-panel-title">解析结果</span>
        <button class="toolbar-btn" @click="handleRefresh" :disabled="store.isParsing">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" :class="{ spinning: store.isParsing }">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
        </button>
      </div>
      
      <!-- Loading State -->
      <div class="parsed-panel-body" v-if="store.isParsing">
        <div class="parsing-loading">
          <div class="parsing-animation">
            <div class="parsing-dot"></div>
            <div class="parsing-dot"></div>
            <div class="parsing-dot"></div>
          </div>
          <div class="parsing-text">{{ progressText }}</div>
          <div class="parsing-hint">正在分析文档结构，请稍候...</div>
        </div>
      </div>
      
      <!-- Parsed Result - 新格式: pages 数组 -->
      <div class="parsed-panel-body" v-else-if="store.parseResult && store.parseResult.pages && store.parseResult.pages.length > 0">
        <div class="parsed-title">{{ store.parseResult.title || '未命名文档' }}</div>
        <div class="parsed-summary" v-if="store.parseResult.subtitle">{{ store.parseResult.subtitle }}</div>
        
        <!-- 页面预览列表 -->
        <div class="pages-preview">
          <div class="pages-preview-header">
            <span class="pages-count">共 {{ store.parseResult.pages.length }} 页</span>
          </div>
          
          <div 
            class="page-preview-item" 
            v-for="(page, index) in store.parseResult.pages" 
            :key="index"
            :class="'page-type-' + page.type"
          >
            <div class="page-preview-header">
              <span class="page-type-badge">{{ getPageTypeName(page.type) }}</span>
              <span class="page-number">第{{ index + 1 }}页</span>
            </div>
            <div class="page-preview-title">{{ page.title || '未命名页面' }}</div>
            <div class="page-preview-subtitle" v-if="page.subtitle">{{ page.subtitle }}</div>
            <ul class="page-preview-bullets" v-if="page.bullets && page.bullets.length">
              <li v-for="(bullet, i) in page.bullets.slice(0, 3)" :key="i">{{ bullet }}</li>
              <li v-if="page.bullets.length > 3" class="more-bullets">...还有 {{ page.bullets.length - 3 }} 项</li>
            </ul>
            <ul class="page-preview-items" v-if="page.items && page.items.length">
              <li v-for="(item, i) in page.items" :key="i">{{ item }}</li>
            </ul>
          </div>
        </div>

        <!-- 开始应用按钮 -->
        <div class="apply-section" v-if="store.parseResult && !isApplying">
          <button class="btn btn-apply" @click="handleApply">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
            开始应用
          </button>
          <span class="apply-hint">保存解析结果并进入大纲编辑</span>
        </div>
        <div class="apply-section" v-else-if="isApplying">
          <div class="applying-status">
            <span class="loading-spinner"></span>
            <span>保存中...</span>
          </div>
        </div>
        <div class="apply-success" v-else-if="isApplied">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
          已保存，点击下方继续
        </div>
      </div>
      
      <!-- Parsed Result - 旧格式: sections 数组 (兼容) -->
      <div class="parsed-panel-body" v-else-if="store.parseResult && store.parseResult.sections">
        <div class="parsed-title">{{ store.parseResult.title || '未命名文档' }}</div>
        <div class="parsed-summary" v-if="store.parseResult.summary">{{ store.parseResult.summary }}</div>

        <div class="parsed-section" v-for="(section, index) in store.parseResult.sections" :key="index">
          <div class="parsed-section-header">
            <div class="parsed-section-icon">{{ getSectionIcon(section.title) }}</div>
            <div class="parsed-section-title">{{ section.title || `第${index + 1}部分` }}</div>
          </div>
          <div class="parsed-section-content" v-if="section.content">{{ section.content }}</div>
          <ul class="parsed-bullets" v-if="section.bullets && section.bullets.length">
            <li v-for="(bullet, i) in section.bullets" :key="i">{{ bullet }}</li>
          </ul>
        </div>

        <div class="parsed-empty" v-if="!store.parseResult.sections || store.parseResult.sections.length === 0">
          <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
            <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
            <p>文档结构简单，<br>将自动生成单页PPT</p>
          </div>
        </div>

        <!-- 开始应用按钮 -->
        <div class="apply-section" v-if="store.parseResult && !isApplying">
          <button class="btn btn-apply" @click="handleApply">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
            开始应用
          </button>
          <span class="apply-hint">保存解析结果并进入大纲编辑</span>
        </div>
        <div class="apply-section" v-else-if="isApplying">
          <div class="applying-status">
            <span class="loading-spinner"></span>
            <span>保存中...</span>
          </div>
        </div>
        <div class="apply-success" v-else-if="isApplied">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
          已保存，点击下方继续
        </div>
      </div>
      
      <!-- Empty State -->
      <div class="parsed-panel-body" v-else>
        <div style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
          <p>粘贴或上传文档后，<br>解析结果将显示在这里</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { store } from '../stores/appStore'

const fileInputRef = ref(null)
const isDragOver = ref(false)
const progressText = ref('正在解析文档...')
const isApplying = ref(false)
const isApplied = ref(false)

// 监听解析状态更新进度文本
watch(() => store.progressText, (newVal) => {
  progressText.value = newVal
})

const updateCharCount = () => {
  store.charCount = store.documentText.length
}

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const handleDragOver = () => {
  isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    handleFile(file)
  }
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) {
    handleFile(file)
  }
}

const handleFile = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    store.documentText = e.target.result
    updateCharCount()
    store.showToastMessage(`已加载：${file.name}`)
  }
  reader.readAsText(file)
}

const handleParse = async () => {
  console.log('handleParse 被调用')
  if (!store.documentText.trim()) {
    console.log('文本为空')
    store.showToastMessage('请先输入或上传文档内容')
    return
  }

  console.log('开始解析，文本长度:', store.documentText.length)
  progressText.value = '正在解析文档...'
  isApplied.value = false
  const result = await store.parseDocument()

  if (result) {
    console.log('解析成功')
    // 不自动跳转，等待用户点击"开始应用"
  } else {
    console.log('解析失败或返回null')
  }
}

const handleRefresh = () => {
  isApplied.value = false
  if (store.parseResult) {
    handleParse()
  }
}

const handleApply = async () => {
  if (!store.currentProject) {
    store.showToastMessage('请先选择或创建项目')
    return
  }

  isApplying.value = true

  try {
    // 1. 保存到 projects 表（原始解析数据）
    const response = await fetch('/api/save-parse-result', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: store.currentProject.id,
        parse_result: store.parseResult,
        original_text: store.documentText
      })
    })

    const data = await response.json()

    if (data.success) {
      // 2. 从 pages 数组生成大纲数据
      const pages = store.parseResult.pages || []
      
      if (pages.length > 0) {
        // 使用新格式的 pages 数组
        const slides = pages.map((page, index) => ({
          page_number: index + 1,
          title: page.title || `第${index + 1}页`,
          subtitle: page.subtitle || page.summary || '',
          content_points: page.bullets || page.items || [],
          // 保持 page.type 原样传递（cover, toc, section, content, end）
          slide_type: page.type || 'content'
        }))
        
        const outlineData = {
          title: store.parseResult.title || '未命名文档',
          slides: slides
        }
        
        // 生成页面数据并保存
        store.replaceOutline(outlineData)
      } else {
        // 兼容旧格式: sections 数组
        const outlineData = {
          slides: store.parseResult.sections.map((section, index) => ({
            page_number: index + 2,
            title: section.title || `第${index + 1}部分`,
            subtitle: section.content || '',
            content_points: section.bullets || [],
            slide_type: 'content'
          }))
        }
        
        // 添加封面页
        outlineData.slides.unshift({
          page_number: 1,
          title: store.parseResult.title || '未命名文档',
          subtitle: store.parseResult.summary || '',
          content_points: [],
          slide_type: 'title'
        })
        
        // 生成页面数据并保存
        store.replaceOutline(outlineData)
      }
      
      await store.saveOutline()

      isApplied.value = true
      store.showToastMessage('解析结果和大纲已保存')
      setTimeout(() => {
        store.nextStep()
      }, 500)
    } else {
      store.showToastMessage(data.error || '保存失败')
    }
  } catch (err) {
    console.error('Save parse result error:', err)
    store.showToastMessage('保存失败，请重试')
  } finally {
    isApplying.value = false
  }
}

const getSectionIcon = (title) => {
  if (!title) return '📑'
  const t = title.toLowerCase()
  if (t.includes('总结') || t.includes('结论') || t.includes('展望')) return '🎯'
  if (t.includes('背景') || t.includes('概述') || t.includes('前言')) return '📖'
  if (t.includes('数据') || t.includes('分析') || t.includes('统计')) return '📊'
  if (t.includes('问题') || t.includes('挑战')) return '⚠️'
  if (t.includes('方案') || t.includes('策略') || t.includes('建议')) return '💡'
  if (t.includes('用户') || t.includes('客户')) return '👥'
  if (t.includes('市场')) return '🌐'
  if (t.includes('产品')) return '📦'
  if (t.includes('财务') || t.includes('营收') || t.includes('利润')) return '💰'
  return '📑'
}

// 获取页面类型的中文名称
const getPageTypeName = (type) => {
  const typeMap = {
    'cover': '封面',
    'toc': '目录',
    'section': '章节',
    'content': '内容',
    'end': '结束'
  }
  return typeMap[type] || '内容'
}
</script>

<style scoped>
.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinning {
  animation: spin 1s linear infinite;
}

.parsing-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-muted);
}

.parsing-animation {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.parsing-dot {
  width: 12px;
  height: 12px;
  background: var(--accent, #6366f1);
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite;
}

.parsing-dot:nth-child(1) { animation-delay: 0s; }
.parsing-dot:nth-child(2) { animation-delay: 0.2s; }
.parsing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.parsing-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.parsing-hint {
  font-size: 13px;
  color: var(--text-muted);
}

.parsed-empty {
  padding: 20px 0;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn:disabled svg,
.btn:disabled .loading-spinner {
  opacity: 0.7;
}

.apply-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color, #e5e7eb);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.btn-apply {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.btn-apply:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.btn-apply:active {
  transform: translateY(0);
}

.apply-hint {
  font-size: 12px;
  color: var(--text-muted, #9ca3af);
}

.applying-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary, #6b7280);
}

.apply-success {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #10b981;
  font-size: 14px;
  font-weight: 500;
}

/* 页面预览样式 */
.pages-preview {
  margin-top: 16px;
}

.pages-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.pages-count {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.page-preview-item {
  background: var(--bg-secondary, #f8fafc);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  border-left: 3px solid var(--accent, #6366f1);
  transition: all 0.2s;
}

.page-preview-item:hover {
  background: var(--bg-hover, #f1f5f9);
}

.page-type-cover { border-left-color: #f59e0b; }
.page-type-toc { border-left-color: #10b981; }
.page-type-section { border-left-color: #6366f1; }
.page-type-content { border-left-color: #64748b; }
.page-type-end { border-left-color: #ef4444; }

.page-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.page-type-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--accent, #6366f1);
  color: white;
  font-weight: 500;
}

.page-type-cover .page-type-badge { background: #f59e0b; }
.page-type-toc .page-type-badge { background: #10b981; }
.page-type-section .page-type-badge { background: #6366f1; }
.page-type-content .page-type-badge { background: #64748b; }
.page-type-end .page-type-badge { background: #ef4444; }

.page-number {
  font-size: 12px;
  color: var(--text-muted);
}

.page-preview-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.page-preview-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.page-preview-bullets,
.page-preview-items {
  margin: 6px 0 0 0;
  padding-left: 18px;
}

.page-preview-bullets li,
.page-preview-items li {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 2px;
}

.more-bullets {
  color: var(--text-muted) !important;
  font-style: italic;
}
</style>
