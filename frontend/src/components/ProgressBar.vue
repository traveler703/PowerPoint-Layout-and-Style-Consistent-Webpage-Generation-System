<template>
  <div class="progress-overlay">
    <div class="progress-card">
      <div class="progress-header">
        <span class="progress-title">正在生成PPT</span>
        <span class="progress-count">{{ safeCurrent }} / {{ safeTotal }}</span>
      </div>
      <div class="progress-bar" role="progressbar" :aria-valuenow="safeCurrent" aria-valuemin="0" :aria-valuemax="safeTotal">
        <div class="progress-bar__inner" :style="{ width: `${progressPercentage}%` }"></div>
      </div>
      <div class="progress-footer">
        已完成 {{ progressPercentage }}%
      </div>
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
.progress-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(4px);
}

.progress-card {
  width: min(520px, calc(100vw - 48px));
  padding: 24px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.22);
}

.progress-header,
.progress-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #334155;
}

.progress-title {
  font-size: 18px;
  font-weight: 700;
}

.progress-count {
  font-size: 16px;
  font-weight: 700;
  color: #0f766e;
}

.progress-bar {
  width: 100%;
  height: 16px;
  margin: 18px 0 12px;
  background-color: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar__inner {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #14b8a6, #22c55e);
  transition: width 0.3s ease;
}

.progress-footer {
  justify-content: flex-end;
  font-size: 13px;
}
</style>
