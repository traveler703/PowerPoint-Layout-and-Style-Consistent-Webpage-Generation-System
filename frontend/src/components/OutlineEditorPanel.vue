<template>
  <div class="outline-editor">
    <!-- Outline Tree Panel -->
    <div class="outline-tree-panel">
      <div class="outline-tree-header">
        <h4>内容大纲</h4>
        <div class="outline-tree-toolbar">
          <!-- 保存状态指示器 -->
          <span v-if="saveStatus === 'saving'" class="save-status saving">
            <span class="save-spinner"></span>
            保存中
          </span>
          <span v-else-if="saveStatus === 'saved'" class="save-status saved">
            ✓ 已保存
          </span>
          <span v-else-if="saveStatus === 'error'" class="save-status error">
            ✗ 保存失败
          </span>
          <button class="toolbar-btn" title="保存大纲" @click="saveOutline">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
            </svg>
          </button>
          <button class="toolbar-btn" title="导入大纲" @click="importOutline">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
            </svg>
          </button>
          <button class="toolbar-btn" title="展开全部" @click="toggleAllOutline">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
            </svg>
          </button>
          <button class="toolbar-btn" title="添加页面" @click="addNewPage">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
          </button>
          <button class="toolbar-btn" title="自动优化" @click="autoOptimize">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="outline-tree-body">
        <div v-for="page in store.pages" :key="page.id" class="outline-node">
          <div
            class="outline-node-content"
            :class="{ selected: store.currentPageId === page.id }"
            @click="selectPage(page.id)"
          >
            <div class="outline-expand hidden">▼</div>
            <div class="outline-icon" :class="page.layout === 'cover' ? 'cover' : 'content'">{{ getPageIcon(page.layout) }}</div>
            <div class="outline-text">
              <div class="outline-title">{{ page.title }}</div>
              <div class="outline-subtitle">{{ getLayoutName(page.layout) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Page Editor Panel -->
    <div class="page-editor-panel">
      <div class="page-editor-header">
        <div class="page-editor-header-left">
          <h4>{{ currentPage?.title || '编辑页面' }}</h4>
          <span class="page-badge">第 {{ currentPageIndex + 1 }} 页</span>
        </div>
        <div class="page-editor-toolbar">
          <button class="toolbar-btn" title="上移" @click="movePageUp">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
            </svg>
          </button>
          <button class="toolbar-btn" title="下移" @click="movePageDown">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
            </svg>
          </button>
          <button class="toolbar-btn" title="删除页面" @click="deleteCurrentPage">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
          <button class="toolbar-btn" title="复制页面" @click="duplicateCurrentPage">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="page-editor-body" v-if="currentPage">
        <!-- Basic Info -->
        <div class="editor-section">
          <div class="editor-section-header">
            <span class="editor-section-title">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              基本信息
            </span>
          </div>
          <div class="text-input-group">
            <label class="text-input-label">页面标题</label>
            <input type="text" class="text-input" v-model="currentPage.title" @change="autoSave">
          </div>
          <div class="text-input-group">
            <label class="text-input-label">副标题</label>
            <input type="text" class="text-input" v-model="currentPage.subtitle" @change="autoSave">
          </div>
        </div>

        <!-- Page Image -->
        <div class="editor-section">
          <div class="editor-section-header">
            <span class="editor-section-title">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              页面图片
            </span>
          </div>
          <div class="image-upload-area" :class="{ 'has-image': currentPage.image }" @click="triggerImageUpload">
            <input type="file" ref="pageImageRef" accept="image/*" style="display: none;" @change="handlePageImageUpload">
            <div class="image-upload-placeholder">
              <div class="image-upload-icon">🖼️</div>
              <div class="image-upload-text">点击上传页面图片</div>
              <div class="image-upload-hint">支持 JPG、PNG，最大 5MB</div>
            </div>
            <div class="image-upload-preview">
              <img :src="currentPage.image" alt="页面图片">
              <div class="image-overlay">
                <button class="image-remove-btn" @click.stop="removePageImage">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                  </svg>
                  移除
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Background & Logo -->
        <div class="editor-section">
          <div class="editor-section-header">
            <span class="editor-section-title">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>
              </svg>
              背景与Logo
            </span>
          </div>
          <div class="logo-upload-area">
            <div class="logo-upload-item">
              <label>背景图片</label>
              <div class="logo-upload-box" :class="{ 'has-logo': currentPage.background }" @click="triggerBgUpload">
                <input type="file" ref="bgImageRef" accept="image/*" style="display: none;" @change="handleBgUpload">
                <svg v-if="!currentPage.background" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                <span v-if="!currentPage.background">背景图</span>
                <img v-if="currentPage.background" :src="currentPage.background" alt="背景">
              </div>
            </div>
            <div class="logo-upload-item">
              <label>公司Logo</label>
              <div class="logo-upload-box" :class="{ 'has-logo': currentPage.logo }" @click="triggerLogoUpload">
                <input type="file" ref="logoImageRef" accept="image/*" style="display: none;" @change="handleLogoUpload">
                <svg v-if="!currentPage.logo" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                </svg>
                <span v-if="!currentPage.logo">Logo</span>
                <img v-if="currentPage.logo" :src="currentPage.logo" alt="Logo">
              </div>
            </div>
          </div>
        </div>

        <!-- Content Bullets -->
        <div class="editor-section">
          <div class="editor-section-header">
            <span class="editor-section-title">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/>
              </svg>
              内容要点
            </span>
          </div>
          <div class="bullet-editor">
            <div v-for="(bullet, index) in currentPage.bullets" :key="index" class="bullet-item">
              <span class="bullet-handle">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"/>
                </svg>
              </span>
              <input type="text" class="text-input" v-model="currentPage.bullets[index]" @change="updateBullet(index)">
              <button class="bullet-remove" @click="removeBullet(index)">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <button class="add-bullet-btn" @click="addBullet">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
              </svg>
              添加要点
            </button>
          </div>
        </div>
      </div>
      <div class="page-editor-body empty-state" v-else>
        <div style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <div style="font-size: 48px; margin-bottom: 16px;">📄</div>
          <p>请选择要编辑的页面<br>或添加新页面</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { store, getPageIcon, getLayoutName } from '../stores/appStore'

const pageImageRef = ref(null)
const bgImageRef = ref(null)
const logoImageRef = ref(null)

const currentPage = computed(() => store.pages.find(p => p.id === store.currentPageId) || null)
const currentPageIndex = computed(() => store.pages.findIndex(p => p.id === store.currentPageId))

// 保存状态: 'idle' | 'saving' | 'saved' | 'error'
const saveStatus = ref('idle')

// 自动保存防抖
let saveTimeout = null
const autoSave = () => {
  if (saveTimeout) clearTimeout(saveTimeout)
  saveStatus.value = 'saving'
  saveTimeout = setTimeout(async () => {
    const result = await store.saveOutlineWithStatus()
    if (result) {
      saveStatus.value = 'saved'
      // 3秒后恢复idle状态
      setTimeout(() => {
        if (saveStatus.value === 'saved') saveStatus.value = 'idle'
      }, 3000)
    } else {
      saveStatus.value = 'error'
      store.showToastMessage('保存失败，请重试')
    }
  }, 1000)
}

const selectPage = (pageId) => {
  store.selectPage(pageId)
}

// 保存大纲到数据库
const saveOutline = async () => {
  console.log('[saveOutline] 开始保存')
  if (saveTimeout) clearTimeout(saveTimeout)
  const result = await store.saveOutline()
  console.log('[saveOutline] 保存结果:', result)
}

// 导入大纲（从文件）
const importOutline = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json,.txt'
  input.onchange = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    try {
      const text = await file.text()
      const data = JSON.parse(text)

      // 支持多种格式
      let outlineData = data
      if (data.outline_data) {
        outlineData = data.outline_data
      }
      if (data.slides) {
        outlineData = { slides: data.slides }
      }

      if (outlineData && outlineData.slides && outlineData.slides.length > 0) {
        store.replaceOutline(outlineData)
        store.showToastMessage('大纲导入成功')
      } else {
        store.showToastMessage('文件格式不正确')
      }
    } catch (err) {
      console.error('导入大纲失败:', err)
      store.showToastMessage('导入失败，请检查文件格式')
    }
  }
  input.click()
}

const updateBullet = (index) => {
  autoSave()
}

const addBullet = () => {
  if (!currentPage.value) return
  if (!currentPage.value.bullets) currentPage.value.bullets = []
  currentPage.value.bullets.push('新要点')
  autoSave()
}

const removeBullet = (index) => {
  if (!currentPage.value || !currentPage.value.bullets) return
  currentPage.value.bullets.splice(index, 1)
}

const triggerImageUpload = () => pageImageRef.value?.click()
const triggerBgUpload = () => bgImageRef.value?.click()
const triggerLogoUpload = () => logoImageRef.value?.click()

const handlePageImageUpload = (e) => {
  const file = e.target.files[0]
  if (file) readFileAsDataURL(file, (result) => {
    currentPage.value.image = result
    store.showToastMessage('页面图片已上传')
  })
}

const handleBgUpload = (e) => {
  const file = e.target.files[0]
  if (file) readFileAsDataURL(file, (result) => {
    currentPage.value.background = result
    store.showToastMessage('背景图片已上传')
  })
}

const handleLogoUpload = (e) => {
  const file = e.target.files[0]
  if (file) readFileAsDataURL(file, (result) => {
    currentPage.value.logo = result
    store.showToastMessage('Logo已上传')
  })
}

const readFileAsDataURL = (file, callback) => {
  const reader = new FileReader()
  reader.onload = (e) => callback(e.target.result)
  reader.readAsDataURL(file)
}

const removePageImage = () => {
  if (currentPage.value) {
    currentPage.value.image = null
    store.showToastMessage('页面图片已移除')
  }
}

const addNewPage = () => {
  store.addPage()
  store.showToastMessage('新页面已添加')
  autoSave()
}

const deleteCurrentPage = () => {
  if (store.pages.length <= 1) {
    store.showToastMessage('至少保留一页')
    return
  }
  if (confirm('确定要删除这一页吗？')) {
    store.deletePage(store.currentPageId)
    store.showToastMessage('页面已删除')
    autoSave()
  }
}

const duplicateCurrentPage = () => {
  store.duplicatePage(store.currentPageId)
  store.showToastMessage('页面已复制')
}

const movePageUp = () => {
  if (store.movePage(store.currentPageId, 'up')) {
    store.showToastMessage('页面上移成功')
  }
}

const movePageDown = () => {
  if (store.movePage(store.currentPageId, 'down')) {
    store.showToastMessage('页面下移成功')
  }
}

const toggleAllOutline = () => {
  store.showToastMessage('大纲已展开')
}

const autoOptimize = () => {
  store.showToastMessage('正在优化大纲结构...')
  setTimeout(() => {
    store.showToastMessage('大纲优化完成')
  }, 1000)
}
</script>
