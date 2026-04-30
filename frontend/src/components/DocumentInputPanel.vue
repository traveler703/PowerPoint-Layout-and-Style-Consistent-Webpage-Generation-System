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
          <div class="drop-zone" :class="{ dragover: isDragOver, uploading: isUploading }">
            <div v-if="isUploading" class="upload-progress">
              <div class="loading-spinner large"></div>
              <div class="upload-progress-text">正在解析文档...</div>
              <div class="upload-progress-filename">{{ uploadingFilename }}</div>
            </div>
            <div v-else-if="uploadedFile" class="upload-success">
              <div class="drop-zone-icon">✅</div>
              <div class="upload-success-text">{{ uploadedFile.name }}</div>
              <div class="upload-success-meta">
                {{ uploadedFile.format.toUpperCase() }} · {{ formatFileSize(uploadedFile.size) }} · {{ uploadedFile.pageCount }}页
              </div>
              <button class="btn btn-sm btn-outline" @click.stop="clearUpload">重新选择</button>
            </div>
            <div v-else>
              <div class="drop-zone-icon">📄</div>
              <div class="drop-zone-text">将文件拖拽到此处，或<span>点击选择文件</span></div>
              <div class="drop-zone-formats">支持 .md .txt .pdf .docx .pptx 格式（最大 20MB）</div>
            </div>
          </div>
          <input type="file" ref="fileInputRef" id="fileInput" accept=".md,.docx,.pdf,.pptx,.txt" style="display: none;" @change="handleFileSelect">
        </div>
      </div>
      <div class="input-panel-footer">
        <span class="input-hint">{{ store.charCount }} 字</span>
        <!-- 粘贴模式：始终显示按钮；上传模式：上传后才显示"重新解析" -->
        <button 
          v-if="store.inputMode === 'paste' || (store.inputMode === 'upload' && uploadedFile)"
          class="btn btn-primary" 
          @click="handleParse"
          :disabled="store.isParsing || isUploading || (store.inputMode === 'paste' && !store.documentText.trim())"
        >
          <span v-if="store.isParsing" class="loading-spinner"></span>
          <svg v-else fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          {{ store.isParsing ? '解析中...' : (store.parseResult ? '重新解析' : '开始解析') }}
        </button>
      </div>
    </div>

    <!-- Parsed Panel -->
    <div class="parsed-panel">
      <div class="parsed-panel-header">
        <span class="input-panel-title">解析结果</span>
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
      
      <!-- Parsed Result -->
      <div class="parsed-panel-body" v-else-if="store.parseResult">
        <div class="parsed-title">{{ store.parseResult.title || '未命名文档' }}</div>
        <div class="parsed-summary" v-if="store.parseResult.summary">{{ store.parseResult.summary }}</div>

        <div class="parsed-section" v-for="(section, index) in store.parseResult.sections" :key="index">
          <div class="parsed-section-header">
            <div class="parsed-section-icon">{{ getSectionIcon(section.title) }}</div>
            <div class="parsed-section-title">{{ section.title || `第${index + 1}部分` }}</div>
          </div>
          <div class="parsed-section-subtitle" v-if="section.subtitle">{{ section.subtitle }}</div>
          <ul class="parsed-bullets" v-if="section.bullets && section.bullets.length">
            <li v-for="(bullet, i) in section.bullets" :key="i">{{ bullet }}</li>
          </ul>
          <div class="parsed-section-content" v-if="section.content">{{ section.content }}</div>
          <div class="parsed-section-tables" v-if="section.tables && section.tables.length">
            <table class="parsed-table" v-for="(tbl, tblIdx) in section.tables" :key="tblIdx">
              <thead>
                <tr>
                  <th v-for="(h, hi) in tbl.headers" :key="hi">{{ h }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in tbl.rows" :key="ri">
                  <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="parsed-section-images" v-if="section.images && section.images.length">
            <img
              v-for="(img, imgIdx) in section.images"
              :key="imgIdx"
              :src="img.url"
              :alt="img.alt || '图片'"
              class="parsed-image"
            />
          </div>
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
import { uploadDocument } from '../services/api'

const fileInputRef = ref(null)
const isDragOver = ref(false)
const progressText = ref('正在解析文档...')
const isApplying = ref(false)
const isApplied = ref(false)
const isUploading = ref(false)
const uploadingFilename = ref('')
const uploadedFile = ref(null)
const originalFileRef = ref(null) // 保存原始 File 对象，用于"重新解析"时重新上传

// 支持的文件格式
const SUPPORTED_EXTENSIONS = ['.md', '.txt', '.pdf', '.docx', '.pptx']
const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20MB

// 监听解析状态更新进度文本
watch(() => store.progressText, (newVal) => {
  progressText.value = newVal
})

const updateCharCount = () => {
  store.charCount = store.documentText.length
}

const triggerFileInput = () => {
  if (!isUploading.value) {
    fileInputRef.value?.click()
  }
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
  // 重置 input 以支持重复选择同一文件
  e.target.value = ''
}

const handleFile = async (file) => {
  // 检查文件格式
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!SUPPORTED_EXTENSIONS.includes(ext)) {
    store.showToastMessage(`不支持的文件格式: ${ext}，请上传 ${SUPPORTED_EXTENSIONS.join(' ')} 格式`)
    return
  }

  // 检查文件大小
  if (file.size > MAX_FILE_SIZE) {
    store.showToastMessage('文件大小超过 20MB 限制')
    return
  }

  isUploading.value = true
  uploadingFilename.value = file.name
  originalFileRef.value = file // 保存原始文件引用

  try {
    // 调用后端上传解析 API
    const response = await uploadDocument(file)

    if (response.success) {
      const result = response.result
      const meta = response.meta

      // 记录上传文件信息
      uploadedFile.value = {
        name: file.name,
        format: meta.format,
        size: meta.file_size,
        pageCount: meta.page_count,
      }

      // 将文档解析结果转换为 store 期望的 parseResult 格式
      const parseResult = convertToParseResult(result)
      store.parseResult = parseResult

      // 设置字符数
      store.charCount = meta.total_chars
      store.documentText = result.pages
        ? result.pages.map(p => p.raw_text || '').join('\n---\n')
        : ''

      store.showToastMessage(`文档解析成功：${meta.page_count} 页`)
    } else {
      store.showToastMessage(response.error || '文档解析失败')
    }
  } catch (err) {
    console.error('Upload document error:', err)
    const errorMsg = err.response?.data?.error || err.message || '文档上传失败'
    store.showToastMessage(errorMsg)
  } finally {
    isUploading.value = false
  }
}

const clearUpload = () => {
  uploadedFile.value = null
  store.parseResult = null
  store.documentText = ''
  store.charCount = 0
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

/**
 * 将后端 DocumentParseResult 转换为前端 store 使用的 parseResult 格式。
 * 核心逻辑：每个 heading 拆分为独立 section（PPT一页），
 * 显示 parent_title 作为页面标题，heading 作为 subtitle，对应段落作为 content。
 */
const convertToParseResult = (docResult) => {
  const pages = docResult.pages || []
  const metadata = docResult.metadata || {}

  const sections = []

  for (const page of pages) {
    const parentTitle = page.title || `第${page.page_index + 1}页`
    const headings = page.headings || []
    const paragraphs = page.paragraphs || []
    const bullets = page.bullets || []

    // 收集图片
    const images = (page.images || []).filter(img => img.url && img.url.length > 0)

    // 收集表格
    const tables = page.tables || []

    if (headings.length === 0) {
      // 无子标题：整页作为一个 section
      const bulletTexts = bullets.map(b => b.description ? `${b.title}：${b.description}` : b.title)
      sections.push({
        title: parentTitle,
        subtitle: '',
        content: paragraphs.join(' '),
        bullets: bulletTexts,
        images: images,
        tables: tables,
      })
    } else {
      // 有子标题：每个子标题拆分为独立 section
      // 如果 headings 之前有段落（概述性文字），先生成一个概述页
      // 然后每个 heading 对应一页
      // 简化处理：按顺序将 paragraphs 分配给对应的 heading
      // （因为解析器按顺序产出 headings 和 paragraphs）
      
      // 如果只有 headings 没有 paragraphs，列出所有 heading 作为 bullets
      if (paragraphs.length === 0 && bullets.length === 0) {
        sections.push({
          title: parentTitle,
          subtitle: '',
          content: '',
          bullets: headings.map(h => h.text),
          images: images,
          tables: tables,
        })
      } else {
        // 有内容：将内容和 headings 组合展示
        const bulletTexts = bullets.map(b => b.description ? `${b.title}：${b.description}` : b.title)
        sections.push({
          title: parentTitle,
          subtitle: headings.map(h => h.text).join(' / '),
          content: paragraphs.join(' '),
          bullets: bulletTexts,
          images: images,
          tables: tables,
        })
      }
    }
  }

  return {
    title: metadata.title || '未命名文档',
    summary: '',
    sections: sections,
  }
}

const handleParse = async () => {
  console.log('handleParse 被调用')
  isApplied.value = false

  // 上传模式：重新上传原始文件（保留格式解析能力）
  if (store.inputMode === 'upload' && originalFileRef.value) {
    console.log('上传模式：重新上传原始文件', originalFileRef.value.name)
    await handleFile(originalFileRef.value)
    return
  }

  // 粘贴模式：发送文本到 /api/parse-text
  if (!store.documentText.trim()) {
    console.log('文本为空')
    store.showToastMessage('请先输入或上传文档内容')
    return
  }

  console.log('开始解析，文本长度:', store.documentText.length)
  progressText.value = '正在解析文档...'
  const result = await store.parseDocument()

  if (result) {
    console.log('解析成功')
  } else {
    console.log('解析失败或返回null')
  }
}

const handleRefresh = () => {
  isApplied.value = false
  // 如果是上传的文件，不重新解析（纯文本解析无法还原原始格式的结构信息）
  if (store.inputMode === 'upload' && uploadedFile.value) {
    store.showToastMessage('文件已解析完成，如需重新解析请重新上传')
    return
  }
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
      // 2. 保存到 outlines 表（结构化大纲）
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

/* 上传相关样式 */
.loading-spinner.large {
  width: 32px;
  height: 32px;
  border-width: 3px;
  border-color: rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  margin: 0 auto 16px;
}

.drop-zone.uploading {
  pointer-events: none;
  opacity: 0.8;
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.upload-progress-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.upload-progress-filename {
  font-size: 13px;
  color: var(--text-muted);
}

.upload-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
}

.upload-success-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.upload-success-meta {
  font-size: 13px;
  color: var(--text-muted);
}

.btn-sm {
  padding: 6px 16px;
  font-size: 12px;
  border-radius: 6px;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border-color, #e5e7eb);
  color: var(--text-secondary, #6b7280);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover {
  border-color: var(--accent, #6366f1);
  color: var(--accent, #6366f1);
}

/* 表格样式 */
.parsed-section-tables {
  margin-top: 10px;
}

.parsed-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border-color, #e5e7eb);
}

.parsed-table th,
.parsed-table td {
  padding: 8px 12px;
  text-align: left;
  border: 1px solid var(--border-color, #e5e7eb);
}

.parsed-table th {
  background: var(--bg-secondary, #f3f4f6);
  font-weight: 600;
  color: var(--text-primary, #374151);
}

.parsed-table td {
  color: var(--text-secondary, #6b7280);
}

.parsed-table tbody tr:hover {
  background: var(--bg-hover, #f9fafb);
}

/* 图片预览样式 */
.parsed-section-images {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.parsed-image {
  max-width: 100%;
  max-height: 150px;
  object-fit: contain;
  border-radius: 6px;
  border: 1px solid var(--border-color, #e5e7eb);
  background: #f9fafb;
}
</style>
