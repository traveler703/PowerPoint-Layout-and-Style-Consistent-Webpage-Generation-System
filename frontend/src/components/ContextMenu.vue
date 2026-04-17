<template>
  <div
    v-if="store.showContextMenu"
    class="context-menu"
    :style="{ left: store.contextMenuPosition.x + 'px', top: store.contextMenuPosition.y + 'px' }"
    @click.stop
  >
    <div class="context-menu-item" @click="openProject">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
      </svg>
      打开项目
    </div>
    <div class="context-menu-item" @click="duplicateProject">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
      </svg>
      复制项目
    </div>
    <div class="context-menu-item" @click="exportProject">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
      </svg>
      导出项目
    </div>
    <div class="context-menu-item" @click="openRenameDialog">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
      </svg>
      重命名
    </div>
    <div style="height: 1px; background: var(--border); margin: 6px 0;"></div>
    <div class="context-menu-item danger" @click="openDeleteDialog">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
      </svg>
      删除项目
    </div>
  </div>

  <!-- 重命名对话框 -->
  <ConfirmDialog
    v-model:visible="renameDialogVisible"
    type="prompt"
    title="重命名项目"
    :message="`将「${currentProject?.name}」重命名为：`"
    :input-value="renameInputValue"
    @update:model-value="renameInputValue = $event"
    confirm-text="确定"
    @confirm="handleRename"
  />

  <!-- 删除确认对话框 -->
  <ConfirmDialog
    v-model:visible="deleteDialogVisible"
    type="danger"
    title="删除项目"
    :message="deleteMessage"
    confirm-text="删除"
    cancel-text="取消"
    @confirm="handleDelete"
  />
</template>

<script setup>
import { ref, computed } from 'vue'
import { store } from '../stores/appStore'
import ConfirmDialog from './ConfirmDialog.vue'

const renameDialogVisible = ref(false)
const deleteDialogVisible = ref(false)
const renameInputValue = ref('')
let deleteProjectId = null
let deleteProjectName = ''

const currentProject = computed(() => {
  return store.projects.find(p => p.id === store.contextMenuProjectId)
})

const deleteMessage = computed(() => {
  return `确定要删除项目「${deleteProjectName}」吗？此操作不可恢复。`
})

const openProject = () => {
  if (store.contextMenuProjectId) {
    store.openProject(store.contextMenuProjectId)
  }
  store.hideContextMenu()
}

const duplicateProject = async () => {
  if (store.contextMenuProjectId) {
    const duplicate = await store.duplicateProject(store.contextMenuProjectId)
    if (duplicate) {
      store.showToastMessage(`项目「${duplicate.name}」已创建`)
    }
  }
  store.hideContextMenu()
}

const exportProject = () => {
  if (store.contextMenuProjectId) {
    const project = store.exportProject(store.contextMenuProjectId)
    if (project) {
      store.showToastMessage(`正在导出项目「${project.name}」...`)
    }
  }
  store.hideContextMenu()
}

const openRenameDialog = () => {
  if (currentProject.value) {
    renameInputValue.value = currentProject.value.name
    renameDialogVisible.value = true
    store.hideContextMenu()
  }
}

const handleRename = async (newName) => {
  if (newName && newName.trim() && store.contextMenuProjectId) {
    const success = await store.renameProject(store.contextMenuProjectId, newName.trim())
    if (success) {
      store.showToastMessage('项目已重命名')
    }
  }
}

const openDeleteDialog = () => {
  // 先保存项目信息，再关闭右键菜单
  deleteProjectId = store.contextMenuProjectId
  deleteProjectName = currentProject.value?.name || ''
  deleteDialogVisible.value = true
  store.hideContextMenu()
}

const handleDelete = async () => {
  if (deleteProjectId) {
    const success = await store.deleteProject(deleteProjectId)
    if (success) {
      store.showToastMessage(`项目「${deleteProjectName}」已删除`)
    }
  }
}
</script>
