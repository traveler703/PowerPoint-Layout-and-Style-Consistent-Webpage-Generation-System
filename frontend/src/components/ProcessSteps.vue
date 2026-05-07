<template>
  <div class="process-steps">
    <div
      v-for="(step, index) in steps"
      :key="index"
      class="step"
      :class="{
        active: currentStep === index + 1,
        completed: currentStep > index + 1
      }"
    >
      <span class="step-number">{{ index + 1 }}</span>
      <span>{{ step }}</span>
    </div>
    <template v-for="(step, index) in steps" :key="'arrow-' + index">
      <span v-if="index < steps.length - 1" class="step-arrow">→</span>
    </template>
  </div>
</template>

<script setup>
defineProps({
  currentStep: {
    type: Number,
    default: 1
  }
})

const steps = ['输入内容', '生成大纲', '生成PPT']
</script>
