<template>
  <div class="project-view active">
    <!-- Header -->
    <header class="project-header">
      <div class="project-header-left">
        <button class="back-btn" @click="store.goToWorkspace()">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
          返回工作空间
        </button>
        <div class="project-title">
          <div class="project-title-icon" :class="store.currentProject?.type">{{ store.currentProject?.icon }}</div>
          <span>{{ store.currentProject?.name }}</span>
        </div>
      </div>
      <div class="project-header-right">
        <button class="btn btn-ghost">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
          </svg>
          分享
        </button>
        <button class="btn btn-ghost" @click="handleExport">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          导出
        </button>
        <button class="btn btn-primary" @click="generatePPT">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
          生成PPT
        </button>
      </div>
    </header>

    <!-- Layout -->
    <div class="project-layout">
      <!-- Sidebar -->
      <aside class="project-sidebar">
        <nav class="workflow-nav">
          <div
            v-for="(step, index) in store.workflowSteps"
            :key="step"
            class="workflow-step"
            :class="{
              active: store.currentStep === step,
              completed: index < currentStepIndex
            }"
            @click="store.setStep(step)"
          >
            <div class="step-indicator">
              <span v-if="index < currentStepIndex">✓</span>
              <span v-else>{{ index + 1 }}</span>
            </div>
            <div class="step-info">
              <div class="step-title">{{ store.stepTitles[step] }}</div>
              <div class="step-desc">{{ stepDescriptions[step] }}</div>
            </div>
          </div>
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="project-main">
        <div class="project-main-header">
          <h2 class="project-main-title">{{ store.stepTitles[store.currentStep] }}</h2>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-ghost" v-if="currentStepIndex > 0" @click="store.prevStep()">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
              </svg>
              上一步
            </button>
            <button
              v-if="!isLastStep"
              class="btn btn-primary"
              @click="handleNextStep"
            >
              {{ isLastStep ? '生成PPT' : '下一步' }}
              <svg v-if="!isLastStep" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </button>
            <button
              v-if="isLastStep"
              class="btn btn-primary"
              :disabled="store.isGenerating"
              @click="generatePPTWithTemplate"
            >
              套用模版生成PPT
            </button>
            <button
              v-if="isLastStep"
              class="btn btn-primary"
              :disabled="store.isGenerating"
              @click="generatePPTPureAI"
            >
              纯AI生成PPT
            </button>
          </div>
        </div>

        <div class="project-main-content">
          <!-- Step 1: Input -->
          <div class="step-panel" :class="{ active: store.currentStep === 'input' }">
            <DocumentInputPanel />
          </div>

          <!-- Step 2: Outline -->
          <div class="step-panel" :class="{ active: store.currentStep === 'outline' }">
            <OutlineEditorPanel />
          </div>

          <!-- Step 3: Style -->
          <div class="step-panel" :class="{ active: store.currentStep === 'style' }">
            <StyleSelectorPanel />
          </div>

          <!-- Step 4: Preview -->
          <div class="step-panel" :class="{ active: store.currentStep === 'preview' }">
            <PreviewPanel />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { store } from '../stores/appStore'
import DocumentInputPanel from './DocumentInputPanel.vue'
import OutlineEditorPanel from './OutlineEditorPanel.vue'
import StyleSelectorPanel from './StyleSelectorPanel.vue'
import PreviewPanel from './PreviewPanel.vue'

const stepDescriptions = {
  input: '粘贴或上传文档',
  outline: '调整内容结构',
  style: '选择视觉主题',
  preview: '查看并下载'
}

const currentStepIndex = computed(() => store.workflowSteps.indexOf(store.currentStep))
const isLastStep = computed(() => currentStepIndex.value === store.workflowSteps.length - 1)

const handleNextStep = () => {
  store.nextStep()
}

const generatePPTWithTemplate = () => {
  store.generatePPTSteam('pipeline')
}

const generatePPTPureAI = () => {
  store.generatePPTSteam('legacy')
}

const handleExport = () => {
  store.showToastMessage('正在导出PPT...')
}
</script>
