<template>
  <div
    v-if="slide"
    style="padding: 20px; font-family: 'Microsoft YaHei', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100%; display: flex; flex-direction: column;"
  >
    <div style="margin-bottom: 12px;">
      <span
        style="background: rgba(255,255,255,0.2); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px;"
      >
        第 {{ index + 1 }} 页 · {{ typeLabel }}
      </span>
    </div>
    <h3 style="color: white; font-size: 20px; margin-bottom: 16px;">
      {{ slide.title || '无标题' }}
    </h3>
    <div style="flex: 1; background: rgba(255,255,255,0.95); border-radius: 8px; padding: 16px;">
      <div
        v-for="(point, i) in points"
        :key="i"
        style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 8px;"
      >
        <span
          style="width: 6px; height: 6px; background: #667eea; border-radius: 50%; margin-top: 7px; flex-shrink: 0;"
        ></span>
        <span style="color: #333; font-size: 14px; line-height: 1.5;">{{ point }}</span>
      </div>
      <p v-if="!points.length" style="color: #999; font-size: 14px;">暂无要点</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  slide: {
    type: Object,
    default: null
  },
  index: {
    type: Number,
    default: 0
  }
})

const typeLabels = {
  'cover': '封面',
  'toc': '目录',
  'section': '章节',
  'content': '内容',
  'end': '结束',
  'title': '标题',
  'agenda': '目录',
  'section_header': '章节',
  'conclusion': '结论',
  'thankyou': '感谢'
}

const typeLabel = computed(() => {
  return typeLabels[props.slide?.slide_type] || props.slide?.slide_type || '内容'
})

const points = computed(() => {
  return props.slide?.content_points || []
})
</script>
