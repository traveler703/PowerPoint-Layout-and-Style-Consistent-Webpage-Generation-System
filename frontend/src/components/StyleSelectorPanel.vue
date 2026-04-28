<template>
  <div class="style-grid">
    <div
      v-for="style in styles"
      :key="style.id"
      class="style-card"
      :class="{ selected: store.selectedStyle === style.id }"
      @click="selectStyle(style.id)"
    >
      <div class="style-preview" :style="{ background: style.gradient }">
        <div class="style-preview-content">
          <div class="style-preview-title" :style="{ color: style.textColor }">{{ style.name }}</div>
          <div class="style-preview-subtitle" :style="{ color: style.subtitleColor }">{{ style.tags }}</div>
        </div>
      </div>
      <div class="style-info">
        <div class="style-name">{{ style.name }}</div>
        <div class="style-desc">{{ style.description }}</div>
        <div class="style-colors">
          <div v-for="color in style.colors" :key="color" class="style-color" :style="{ background: color }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { store } from '../stores/appStore'

const styles = [
  {
    id: 'business',
    name: '商务蓝',
    tags: '专业 · 稳重',
    description: '适合正式汇报、企业提案',
    gradient: 'linear-gradient(135deg, #1e3a5f, #2d5a87)',
    textColor: 'white',
    subtitleColor: 'rgba(255,255,255,0.7)',
    colors: ['#1e3a5f', '#2d5a87', '#4a90d9']
  },
  {
    id: 'academic',
    name: '学术灰',
    tags: '简约 · 清晰',
    description: '适合学术报告、论文答辩',
    gradient: 'linear-gradient(135deg, #4a5568, #718096)',
    textColor: 'white',
    subtitleColor: 'rgba(255,255,255,0.7)',
    colors: ['#4a5568', '#718096', '#a0aec0']
  },
  {
    id: 'vibrant',
    name: '活力橙',
    tags: '活力 · 创意',
    description: '适合创业路演、活动策划',
    gradient: 'linear-gradient(135deg, #dd6b20, #ed8936)',
    textColor: 'white',
    subtitleColor: 'rgba(255,255,255,0.7)',
    colors: ['#dd6b20', '#ed8936', '#f6ad55']
  },
  {
    id: 'tech',
    name: '科技紫',
    tags: '科技 · 神秘',
    description: '适合科技产品、技术分享',
    gradient: 'linear-gradient(135deg, #6b46c1, #9f7aea)',
    textColor: 'white',
    subtitleColor: 'rgba(255,255,255,0.7)',
    colors: ['#6b46c1', '#9f7aea', '#b794f4']
  },
  {
    id: 'nature',
    name: '清新绿',
    tags: '自然 · 健康',
    description: '适合环保、健康主题',
    gradient: 'linear-gradient(135deg, #2f855a, #48bb78)',
    textColor: 'white',
    subtitleColor: 'rgba(255,255,255,0.7)',
    colors: ['#2f855a', '#48bb78', '#68d391']
  },
  {
    id: 'minimal',
    name: '极简白',
    tags: '文艺 · 优雅',
    description: '适合文艺分享、个人展示',
    gradient: 'linear-gradient(135deg, #f7fafc, #edf2f7)',
    textColor: '#1a202c',
    subtitleColor: '#718096',
    colors: ['#f7fafc', '#edf2f7', '#e2e8f0']
  }
]

const selectStyle = (styleId) => {
  store.setStyle(styleId)
}
</script>
