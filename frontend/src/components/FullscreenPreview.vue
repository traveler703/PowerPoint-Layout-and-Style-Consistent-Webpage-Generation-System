<template>
  <div class="fullscreen-preview active" @click.self="$emit('close')">
    <button class="fullscreen-close" @click="$emit('close')">&times;</button>
    <iframe :srcdoc="html" sandbox="allow-same-origin"></iframe>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'

defineProps({
  html: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close'])

function handleKeydown(e) {
  if (e.key === 'Escape') {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.fullscreen-preview iframe {
  width: 1280px;
  height: 720px;
  border: none;
  border-radius: 8px;
  transform: scale(0.9);
}
</style>
