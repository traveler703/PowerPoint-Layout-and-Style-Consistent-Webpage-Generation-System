<template>
  <div class="modal-overlay active" @click.self="store.closeImportModal()">
    <div class="modal">
      <div class="modal-header">
        <h3 class="modal-title">导入项目</h3>
        <button class="modal-close" @click="store.closeImportModal()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <div class="drop-zone" style="margin-bottom: 20px; padding: 40px;" :class="{ dragover: isDragOver }" @dragover.prevent="isDragOver = true" @dragleave="isDragOver = false" @drop.prevent="handleDrop" @click="triggerFileInput">
          <div class="drop-zone-icon">📦</div>
          <div class="drop-zone-text">将项目文件拖拽到此处，或<span>点击选择</span></div>
          <div class="drop-zone-formats">支持 .seem 项目文件格式</div>
        </div>
        <input type="file" ref="fileInputRef" accept=".seem,.zip,.json" style="display: none;" @change="handleFileSelect">
        <p style="font-size: 12px; color: var(--text-muted); text-align: center;">
          导入的项目将合并到您的工作空间
        </p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="store.closeImportModal()">取消</button>
        <button class="btn btn-primary" @click="triggerFileInput">选择文件</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { store } from '../stores/appStore'

const fileInputRef = ref(null)
const isDragOver = ref(false)

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const handleDrop = (e) => {
  isDragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    importProject(file)
  }
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) {
    importProject(file)
  }
}

const importProject = async (file) => {
  store.closeImportModal()
  store.showToastMessage(`正在导入项目「${file.name}」...`)

  try {
    const result = await store.createProject(
      file.name.replace(/\.[^/.]+$/, ''),
      'business'
    )
    if (result) {
      store.showToastMessage('项目导入成功')
    }
  } catch (err) {
    console.error('Import project error:', err)
    store.showToastMessage('项目导入失败')
  }
}
</script>
