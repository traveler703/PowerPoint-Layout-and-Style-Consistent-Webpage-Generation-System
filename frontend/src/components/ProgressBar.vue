<template>
  <div class="progress-strip">
    <span class="progress-strip-label">生成中 {{ safeCurrent }}/{{ safeTotal }}</span>
    <div class="progress-strip-bar" role="progressbar" :aria-valuenow="safeCurrent" aria-valuemin="0" :aria-valuemax="safeTotal">
      <div class="progress-strip-fill" :style="{ width: `${progressPercentage}%` }"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  current: {
    type: Number,
    required: true
  },
  total: {
    type: Number,
    required: true
  }
})

const safeTotal = computed(() => Math.max(Number(props.total) || 0, 1))
const safeCurrent = computed(() => Math.min(Math.max(Number(props.current) || 0, 0), safeTotal.value))

const progressPercentage = computed(() => {
  return Math.min(Math.round((safeCurrent.value / safeTotal.value) * 100), 100)
})
</script>

<style scoped>
.progress-strip {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 20px;
  background: rgba(9, 9, 11, 0.92);
  border-bottom: 1px solid rgba(99, 102, 241, 0.3);
  pointer-events: none;
}
.progress-strip-label {
  font-size: 12px;
  color: #a1a1aa;
  white-space: nowrap;
}
.progress-strip-bar {
  flex: 1;
  height: 4px;
  background: rgba(99, 102, 241, 0.15);
  border-radius: 2px;
  overflow: hidden;
}
.progress-strip-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  transition: width 0.3s ease;
}
</style>
