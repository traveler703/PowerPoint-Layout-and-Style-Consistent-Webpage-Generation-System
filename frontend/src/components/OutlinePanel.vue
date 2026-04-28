<template>
  <div class="panel outline-panel">
    <h2 class="panel-title">
      编辑大纲
      <span class="outline-title-text">{{ outline?.title || 'PPT大纲' }}</span>
    </h2>

    <div class="outline-info">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4M12 8h.01" />
      </svg>
      <span>编辑大纲后点击"生成PPT"开始生成</span>
    </div>

    <div class="action-buttons">
      <button
        class="btn btn-success"
        :disabled="isGenerating"
        @click="$emit('generate-ppt')"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
        生成PPT
      </button>
      <button class="btn btn-secondary" @click="$emit('reset')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 019-9 9 9 0 016.36 2.64" />
          <path d="M21 3v6h-6" />
        </svg>
        重新开始
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  outline: {
    type: Object,
    default: null
  },
  currentSlideIndex: {
    type: Number,
    default: 0
  },
  isGenerating: {
    type: Boolean,
    default: false
  }
})

defineEmits(['generate-ppt', 'reset'])
</script>

<style scoped>
.outline-panel {
  margin-top: 20px;
}

.outline-title-text {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: normal;
}
</style>
