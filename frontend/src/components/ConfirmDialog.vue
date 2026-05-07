<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="dialog-overlay" @click.self="handleCancel">
        <div class="dialog-container" :class="type">
          <div class="dialog-header">
            <span class="dialog-icon" v-if="type === 'danger'">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
            </span>
            <span class="dialog-icon" v-else-if="type === 'prompt'">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </span>
            <span class="dialog-title">{{ title }}</span>
          </div>
          <div class="dialog-body">
            <p v-if="message" class="dialog-message">{{ message }}</p>
            <input
              v-if="type === 'prompt'"
              ref="inputRef"
              v-model="localInputValue"
              class="dialog-input"
              :placeholder="placeholder"
              @keyup.enter="handleConfirm"
              @keyup.escape="handleCancel"
            />
          </div>
          <div class="dialog-footer">
            <button class="dialog-btn cancel" @click="handleCancel">
              {{ cancelText }}
            </button>
            <button
              class="dialog-btn confirm"
              :class="type"
              @click="handleConfirm"
              ref="confirmBtn"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  type: { type: String, default: 'confirm' }, // confirm, danger, prompt
  title: { type: String, default: '确认' },
  message: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  inputValue: { type: String, default: '' }
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

const localInputValue = ref(props.inputValue)
const inputRef = ref(null)

watch(() => props.inputValue, (val) => {
  localInputValue.value = val
})

watch(() => props.visible, async (val) => {
  if (val) {
    localInputValue.value = props.inputValue
    if (props.type === 'prompt') {
      await nextTick()
      inputRef.value?.focus()
    }
  }
})

const handleConfirm = () => {
  emit('confirm', props.type === 'prompt' ? localInputValue.value : null)
  emit('update:visible', false)
}

const handleCancel = () => {
  emit('cancel')
  emit('update:visible', false)
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.dialog-container {
  background: var(--bg-secondary, #1e1e2e);
  border: 1px solid var(--border, #3a3a4a);
  border-radius: 12px;
  padding: 24px;
  min-width: 360px;
  max-width: 480px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.dialog-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary, #2a2a3a);
}

.dialog-icon svg {
  width: 20px;
  height: 20px;
  color: var(--text-secondary, #a0a0b0);
}

.dialog-container.danger .dialog-icon {
  background: rgba(239, 68, 68, 0.15);
}

.dialog-container.danger .dialog-icon svg {
  color: #ef4444;
}

.dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #f0f0f5);
}

.dialog-body {
  margin-bottom: 20px;
}

.dialog-message {
  font-size: 14px;
  color: var(--text-secondary, #a0a0b0);
  line-height: 1.6;
  margin: 0;
}

.dialog-input {
  width: 100%;
  margin-top: 12px;
  padding: 12px 14px;
  background: var(--bg-primary, #181820);
  border: 1px solid var(--border, #3a3a4a);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary, #f0f0f5);
  outline: none;
  transition: border-color 0.2s;
}

.dialog-input:focus {
  border-color: var(--accent, #6366f1);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.dialog-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.dialog-btn.cancel {
  background: var(--bg-tertiary, #2a2a3a);
  color: var(--text-secondary, #a0a0b0);
}

.dialog-btn.cancel:hover {
  background: var(--bg-primary, #181820);
  color: var(--text-primary, #f0f0f5);
}

.dialog-btn.confirm {
  background: var(--accent, #6366f1);
  color: white;
}

.dialog-btn.confirm:hover {
  opacity: 0.9;
}

.dialog-btn.confirm.danger {
  background: #ef4444;
}

.dialog-btn.confirm.danger:hover {
  background: #dc2626;
}

/* 动画 */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .dialog-container,
.modal-leave-to .dialog-container {
  transform: scale(0.95);
}
</style>
