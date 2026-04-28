<template>
  <div v-if="store.showToast" class="toast-wrapper">
    <div class="toast" :class="{ 'toast-show': store.showToast }">
      <div class="toast-icon">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
        </svg>
      </div>
      <span class="toast-message">{{ store.toastMessage }}</span>
    </div>
  </div>
</template>

<script setup>
import { store } from '../stores/appStore'
</script>

<style scoped>
.toast-wrapper {
  position: fixed;
  bottom: 24px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  pointer-events: none;
  z-index: 10000;
}

.toast {
  background: #10b981;
  border-radius: 8px;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.3s ease;
}

.toast-show {
  opacity: 1;
  transform: translateY(0);
}

.toast-icon {
  color: white;
  display: flex;
  align-items: center;
}

.toast-message {
  font-size: 14px;
  color: white;
  font-weight: 500;
  white-space: nowrap;
}
</style>
