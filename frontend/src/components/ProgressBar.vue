<template>
  <div class="progress-inline">
    <span class="progress-inline-label">{{ safeCurrent }}/{{ safeTotal }}</span>
    <div class="progress-inline-bar" role="progressbar" :aria-valuenow="safeCurrent" aria-valuemin="0" :aria-valuemax="safeTotal">
      <div class="progress-inline-fill" :style="{ width: `${progressPercentage}%` }"></div>
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
.progress-inline {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 12px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 6px;
  min-width: 160px;
}
.progress-inline-label {
  font-size: 11px;
  color: #a1a1aa;
  white-space: nowrap;
  font-weight: 600;
}
.progress-inline-bar {
  flex: 1;
  height: 4px;
  background: rgba(99, 102, 241, 0.12);
  border-radius: 2px;
  overflow: hidden;
  min-width: 60px;
}
.progress-inline-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  transition: width 0.3s ease;
}
</style>
