<template>
  <div class="panel">
    <!-- Tab切换 -->
    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'outline' }"
        @click="$emit('switch-tab', 'outline')"
      >
        大纲
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'preview' }"
        @click="$emit('switch-tab', 'preview')"
      >
        预览
      </button>
    </div>

    <!-- 大纲Tab -->
    <div class="tab-content" :class="{ active: activeTab === 'outline' }">
      <div v-if="!currentOutline" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
        <p>输入内容并生成大纲后<br>可在此查看和编辑大纲</p>
      </div>

      <div v-else class="outline-editor">
        <div class="slide-viewer">
          <div class="slide-frame">
            <OutlineSlidePreview
              :slide="currentOutline.slides?.[outlineSlideIndex]"
              :index="outlineSlideIndex"
            />
          </div>
          <div class="slide-nav">
            <button
              class="slide-nav-btn"
              :disabled="outlineSlideIndex === 0"
              @click="$emit('prev-slide')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M15 18l-6-6 6-6" />
              </svg>
              上一页
            </button>
            <span class="slide-indicator">
              <strong>{{ outlineSlideIndex + 1 }}</strong> / {{ currentOutline.slides?.length || 1 }}
            </span>
            <button
              class="slide-nav-btn"
              :disabled="outlineSlideIndex >= (currentOutline.slides?.length || 1) - 1"
              @click="$emit('next-slide')"
            >
              下一页
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览Tab -->
    <div class="tab-content" :class="{ active: activeTab === 'preview' }">
      <div v-if="!currentSlides.length && !isGenerating" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
        <p>点击"生成PPT"后<br>可在此实时预览生成的幻灯片</p>
      </div>

      <div v-else class="preview-area">
        <div class="slide-viewer">
          <div class="slide-frame">
            <div v-if="isGenerating && currentSlides.length === 0" class="loading-overlay">
              <div class="spinner"></div>
              <div class="status-message">正在生成第 {{ generationProgress.current || 1 }} 页...</div>
            </div>
            <iframe
              v-if="currentSlides[previewSlideIndex]"
              :srcdoc="currentSlides[previewSlideIndex].html"
              sandbox="allow-same-origin"
            ></iframe>
          </div>
          <div class="slide-nav">
            <button
              class="slide-nav-btn"
              :disabled="previewSlideIndex === 0"
              @click="$emit('prev-preview')"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M15 18l-6-6 6-6" />
              </svg>
              上一页
            </button>
            <span class="slide-indicator">
              <strong>{{ previewSlideIndex + 1 }}</strong> / {{ currentSlides.length || 1 }}
            </span>
            <button
              class="slide-nav-btn"
              :disabled="previewSlideIndex >= (currentSlides.length || 1) - 1"
              @click="$emit('next-preview')"
            >
              下一页
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </button>
            <button class="slide-nav-btn" @click="$emit('open-fullscreen')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" />
              </svg>
              全屏
            </button>
          </div>
        </div>

        <!-- 缩略图列表 -->
        <div v-if="currentSlides.length" class="thumbnails">
          <div
            v-for="(slide, index) in currentSlides"
            :key="index"
            class="thumbnail"
            :class="{ active: index === previewSlideIndex }"
            @click="$emit('go-to-slide', index)"
          >
            <iframe :srcdoc="escapeHtmlForAttr(slide.html)"></iframe>
          </div>
        </div>

        <!-- 生成进度 -->
        <div v-if="isGenerating" class="generation-progress">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: progressPercent + '%' }"
            ></div>
          </div>
          <div class="progress-text">{{ generationProgress.text }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import OutlineSlidePreview from './OutlineSlidePreview.vue'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'outline'
  },
  currentOutline: {
    type: Object,
    default: null
  },
  currentSlides: {
    type: Array,
    default: () => []
  },
  previewSlideIndex: {
    type: Number,
    default: 0
  },
  outlineSlideIndex: {
    type: Number,
    default: 0
  },
  isGenerating: {
    type: Boolean,
    default: false
  },
  generationProgress: {
    type: Object,
    default: () => ({ current: 0, total: 1, text: '' })
  }
})

const emit = defineEmits([
  'switch-tab',
  'go-to-slide',
  'prev-preview',
  'next-preview',
  'open-fullscreen',
  'prev-slide',
  'next-slide'
])

const progressPercent = computed(() => {
  if (!props.generationProgress.total) return 0
  return (props.generationProgress.current / props.generationProgress.total) * 100
})

function escapeHtmlForAttr(text) {
  return text
    ?.replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;') || ''
}
</script>

<style scoped>
.preview-area {
  display: block;
}

.preview-area iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
