<template>
  <div class="app active">
    <!-- Workspace View -->
    <WorkspaceView v-if="store.currentView === 'workspace'" />

    <!-- Project View -->
    <ProjectView v-else-if="store.currentView === 'project'" />

    <!-- Context Menu -->
    <ContextMenu />

    <!-- Toast -->
    <Toast />

    <!-- New Project Modal -->
    <NewProjectModal v-if="store.showNewProjectModal" />

    <!-- Import Modal -->
    <ImportModal v-if="store.showImportModal" />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { store } from './stores/appStore'
import WorkspaceView from './components/WorkspaceView.vue'
import ProjectView from './components/ProjectView.vue'
import ContextMenu from './components/ContextMenu.vue'
import Toast from './components/Toast.vue'
import NewProjectModal from './components/NewProjectModal.vue'
import ImportModal from './components/ImportModal.vue'

// Global keyboard shortcuts
const handleKeydown = (e) => {
  if (e.key === 'Escape') {
    store.showNewProjectModal = false
    store.showImportModal = false
    store.hideContextMenu()
  }
}

// Close context menu on click outside
const handleClick = () => {
  if (store.showContextMenu) {
    store.hideContextMenu()
  }
}

onMounted(async () => {
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('click', handleClick)
  // 从数据库加载项目列表
  await store.init()
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('click', handleClick)
})
</script>
