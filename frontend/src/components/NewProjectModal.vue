<template>
  <div class="modal-overlay active" @click.self="store.closeNewProjectModal()">
    <div class="modal">
      <div class="modal-header">
        <h3 class="modal-title">新建项目</h3>
        <button class="modal-close" @click="store.closeNewProjectModal()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">项目名称</label>
          <input
            type="text"
            class="form-input"
            v-model="projectName"
            placeholder="输入项目名称..."
            @keyup.enter="createProject"
          >
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="store.closeNewProjectModal()">取消</button>
        <button class="btn btn-primary" @click="createProject">创建项目</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { store } from '../stores/appStore'

const projectName = ref('')

const createProject = async () => {
  const newProject = await store.createProject(projectName.value || '未命名项目')
  store.closeNewProjectModal()

  if (newProject) {
    store.showToastMessage(`项目「${newProject.name}」已创建`)
    // Open the new project after a short delay
    setTimeout(() => {
      store.openProject(newProject.id)
    }, 500)
  }
}
</script>
