<template>
  <div class="panel">
    <h2 class="panel-title">输入内容</h2>

    <div class="form-group">
      <label>文本内容</label>
      <textarea
        v-model="content"
        placeholder="请输入您想要制作PPT的文本内容，AI将自动分析并生成合适的大纲..."
      ></textarea>
    </div>

    <div class="form-row">
      <div class="form-group">
        <label>场景</label>
        <select v-model="scenario">
          <option value="technology">科技技术</option>
          <option value="business">商业商务</option>
          <option value="education">教育培训</option>
          <option value="medical">医疗健康</option>
          <option value="finance">金融投资</option>
          <option value="marketing">市场营销</option>
          <option value="report" selected>分析报告</option>
          <option value="general">通用场景</option>
        </select>
      </div>

      <div class="form-group">
        <label>受众</label>
        <input
          v-model="audience"
          type="text"
          placeholder="例如：技术从业者"
        />
      </div>
    </div>

    <div class="form-group">
      <label>风格</label>
      <select v-model="style">
        <option value="modern" selected>现代简约</option>
        <option value="classic">经典商务</option>
        <option value="minimal">极简主义</option>
        <option value="professional">专业严谨</option>
        <option value="creative">创意活泼</option>
      </select>
    </div>

    <div class="btn-group">
      <button
        class="btn btn-primary"
        :disabled="isGeneratingOutline"
        @click="handleGenerate"
      >
        <svg
          v-if="!isGeneratingOutline"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
          <rect x="9" y="3" width="6" height="4" rx="1" />
          <path d="M9 12h6M9 16h6" />
        </svg>
        <div v-else class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>
        {{ isGeneratingOutline ? '生成中...' : '生成大纲' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  isGeneratingOutline: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['generate-outline'])

const content = ref('')
const scenario = ref('report')
const audience = ref('')
const style = ref('modern')

function handleGenerate() {
  if (!content.value.trim()) {
    alert('请输入文本内容')
    return
  }

  emit('generate-outline', {
    topic: content.value,
    scenario: scenario.value,
    audience: audience.value || '通用受众',
    page_count: 10
  })
}
</script>
