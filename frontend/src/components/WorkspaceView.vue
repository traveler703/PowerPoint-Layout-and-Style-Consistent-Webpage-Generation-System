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
            <span class="workspace-stat-value">{{ store.projects.length }}</span>
            <span>个项目</span>
          </div>
          <div class="workspace-stat">
            <span class="workspace-stat-value">{{ store.totalSlidesCount }}</span>
            <span>张幻灯片</span>
          </div>
        </div>
      </div>
      <div class="workspace-header-right">
        <button class="btn btn-secondary" @click="store.openImportModal()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
          </svg>
          导入项目
        </button>
        <button class="btn btn-primary" @click="store.openNewProjectModal()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          新建项目
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
            <input type="text" placeholder="搜索项目..." v-model="store.searchQuery">
          </div>
          <button class="filter-btn" @click="sortProjects">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12"/>
            </svg>
            排序
          </button>
        </div>
        <div class="toolbar-right">
          <div class="view-toggle">
            <button class="view-toggle-btn" :class="{ active: store.viewMode === 'grid' }" @click="store.setViewMode('grid')">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
              </svg>
            </button>
            <button class="view-toggle-btn" :class="{ active: store.viewMode === 'list' }" @click="store.setViewMode('list')">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Projects Grid/List -->
      <div v-if="filteredProjects.length > 0" class="projects-container" :class="store.viewMode === 'grid' ? 'projects-grid' : 'projects-list'">
        <div
          v-for="project in filteredProjects"
          :key="project.id"
          class="project-card"
          :class="{ 'list-mode': store.viewMode === 'list' }"
          @click="store.openProject(project.id)"
          @contextmenu.prevent="showContextMenu($event, project.id)"
        >
          <div class="project-card-header">
            <div class="project-icon" :class="project.type">{{ project.icon }}</div>
            <button class="project-menu-btn" @click.stop="showContextMenu($event, project.id)">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"/>
              </svg>
            </button>
          </div>
          <div class="project-preview">
            <div class="project-preview-text">{{ project.icon }}</div>
          </div>
          <div class="project-name">{{ project.name }}</div>
          <div class="project-desc">{{ project.desc }}</div>
          <div class="project-meta">
            <div class="project-meta-item">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              {{ project.pages }}页
            </div>
            <div class="project-meta-item">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              {{ formatTime(project.updated) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <div class="empty-state-icon">📊</div>
        <h3>还没有项目</h3>
        <p>创建您的第一个项目，开始使用PPT Studio快速生成专业PPT。</p>
        <button class="btn btn-primary" @click="store.openNewProjectModal()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          新建项目
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store, filteredProjects, formatTime } from '../stores/appStore'

const sortProjects = () => {
  store.projects.sort((a, b) => b.updated - a.updated)
  store.showToastMessage('已按更新时间排序')
}

const showContextMenu = (event, projectId) => {
  store.contextMenuProjectId = projectId
  store.contextMenuPosition = { x: event.clientX, y: event.clientY }
  store.showContextMenu = true
}
</script>

<style scoped>
.project-card.list-mode {
  flex-direction: row;
  height: auto;
}

.project-card.list-mode .project-preview {
  width: 120px;
  height: 80px;
  flex-shrink: 0;
}
</style>
