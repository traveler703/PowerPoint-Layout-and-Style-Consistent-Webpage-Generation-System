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
      <div class="project-header-right"></div>
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
              v-if="showNextButton"
              class="btn btn-primary"
              @click="handleNextStep"
            >
              下一步
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </button>
            <button
              v-if="store.currentStep === 'preview'"
              class="btn btn-primary"
              :disabled="store.isGenerating"
              @click="generatePPTParallel"
            >
              生成PPT
            </button>
            <button
              v-if="store.currentStep === 'preview'"
              class="btn btn-ghost"
              @click="store.setStep('report')"
            >
              查看报告
            </button>
            <button
              v-if="store.currentStep === 'report'"
              class="btn btn-primary"
              :disabled="store.isEvaluating"
              @click="store.evaluateGeneratedPresentation()"
            >
              {{ store.isEvaluating ? '评估中...' : '刷新报告' }}
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

          <!-- Step 5: Report -->
          <div class="step-panel" :class="{ active: store.currentStep === 'report' }">
            <ReportPanel />
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
import ReportPanel from './ReportPanel.vue'

const stepDescriptions = {
  input: '粘贴或上传文档',
  outline: '调整内容结构',
  style: '选择PPT模板',
  preview: '查看并下载',
  report: '检查质量指标'
}

const currentStepIndex = computed(() => store.workflowSteps.indexOf(store.currentStep))
const isLastStep = computed(() => currentStepIndex.value === store.workflowSteps.length - 1)
const showNextButton = computed(() => !isLastStep.value && store.currentStep !== 'preview')

const handleNextStep = () => {
  store.nextStep()
}

const generatePPTParallel = () => {
  store.generatePPTParallel()
}

</script>
