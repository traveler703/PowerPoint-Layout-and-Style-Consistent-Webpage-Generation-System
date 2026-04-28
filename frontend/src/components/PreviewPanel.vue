<template>
  <div class="preview-container">
    <!-- Left: Page Thumbnails -->
    <div class="preview-pages-panel">
      <div class="preview-pages-header">
        <h4>所有页面</h4>
        <span class="page-count">{{ store.pages.length }} 页</span>
      </div>
      <div class="preview-pages-body">
        <div
          v-for="(page, index) in store.pages"
          :key="page.id"
          class="preview-page-thumb"
          :class="{ active: store.currentSlide === page.id }"
          @click="goToSlide(page.id)"
        >
          <div class="preview-page-thumb-preview" :class="{ 'layout-content': page.layout === 'content' }">
            <!-- 如果有生成的HTML，显示缩略图预览 -->
            <div v-if="getSlideHtml(page.pageNumber || page.id)" class="thumb-html-preview">
              <iframe
                :srcdoc="getSlideHtml(page.pageNumber || page.id)"
                class="thumb-iframe"
                sandbox="allow-same-origin"
              ></iframe>
            </div>
            <img v-else-if="page.image" :src="page.image" alt="">
            <span v-else>{{ getPageIcon(page.layout) }}</span>
          </div>
          <div class="preview-page-thumb-info">
            <span class="preview-page-thumb-title">{{ page.title }}</span>
            <span class="preview-page-thumb-num">{{ index + 1 }}/{{ store.pages.length }}</span>
            <!-- 生成状态指示器 -->
            <span v-if="store.isGenerating && (page.id === store.currentGeneratingPage || store.currentGeneratingPage > index + 1)" class="generation-status">
              <span v-if="store.currentGeneratingPage === index + 1" class="generating">生成中...</span>
              <span v-else-if="store.currentGeneratingPage > index + 1" class="generated">✓</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right: Main Preview -->
    <div class="preview-main-panel">
      <div class="preview-main-header">
        <span style="font-size: 14px; font-weight: 600;">
          第 {{ currentSlideIndex + 1 }} 页 / {{ store.pages.length }} 页
        </span>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-ghost" style="padding: 6px 12px; font-size: 12px;" @click="prevSlide" :disabled="currentSlideIndex === 0">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
            上一页
          </button>
          <button class="btn btn-ghost" style="padding: 6px 12px; font-size: 12px;" @click="nextSlide" :disabled="currentSlideIndex === store.pages.length - 1">
            下一页
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
            </svg>
          </button>
          <button
            class="btn btn-primary"
            style="padding: 6px 12px; font-size: 12px;"
            @click="downloadPPT"
            :disabled="!hasGeneratedSlides || store.isGenerating"
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            下载PPT
          </button>
          <button
            class="btn btn-primary"
            style="padding: 6px 12px; font-size: 12px;"
            @click="savePPT"
            :disabled="!hasGeneratedSlides || store.isGenerating"
          >
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
            </svg>
            保存PPT
          </button>
        </div>
      </div>
      <div v-if="hasGeneratedSlides" class="evaluation-bar">
        <div class="evaluation-item">
          <span class="evaluation-label">当前页评估</span>
          <span class="evaluation-value" :class="{ pass: currentSlideEvaluation?.passed, fail: currentSlideEvaluation && !currentSlideEvaluation.passed }">
            {{ currentSlideEvaluation ? (currentSlideEvaluation.passed ? '通过' : '警告') : '暂无' }}
          </span>
        </div>
        <div class="evaluation-item">
          <span class="evaluation-label">重叠率</span>
          <span class="evaluation-value">{{ currentOverlapText }}</span>
        </div>
        <div class="evaluation-item">
          <span class="evaluation-label">颜色偏差</span>
          <span class="evaluation-value">{{ currentColorDeviationText }}</span>
        </div>
        <div class="evaluation-item">
          <span class="evaluation-label">全局通过率</span>
          <span class="evaluation-value">{{ evaluationPassRate }}</span>
        </div>
      </div>
      <div class="preview-main-body">
        <!-- 生成进度显示 -->
        <div v-if="store.isGenerating" class="generating-overlay">
          <div class="generating-progress">
            <div class="progress-text">正在生成第 {{ store.currentGeneratingPage }} / {{ store.totalPagesToGenerate }} 页</div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: store.progressPercent + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- 如果有生成的HTML，使用iframe显示 -->
        <div v-if="currentSlideHtml" ref="iframeContainer" class="preview-slide-iframe-container">
          <div class="iframe-scale-wrapper" :style="scaleStyle">
            <iframe
              ref="slideIframe"
              :key="iframeKey"
              :srcdoc="currentSlideHtml"
              class="preview-slide-iframe"
              sandbox="allow-same-origin allow-scripts"
              @load="onIframeLoad"
            ></iframe>
          </div>
        </div>

        <!-- 否则显示默认预览 -->
        <div
          v-if="!currentSlideHtml"
          class="preview-slide-display"
          :style="slideStyle"
        >
          <h1>{{ currentSlidePage?.title }}</h1>
          <p>{{ currentSlidePage?.subtitle }}</p>
          <div class="preview-slide-bullets" v-if="currentSlidePage?.bullets?.length > 0">
            <span v-for="(bullet, index) in currentSlidePage?.bullets?.slice(0, 4)" :key="index">• {{ bullet }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { store, getPageIcon } from '../stores/appStore'

const slideIframe = ref(null)
const iframeContainer = ref(null)
const scale = ref(1) // 初始值1，计算后会正确缩放
const iframeLoaded = ref(true) // iframe加载状态

// 计算缩放比例
const calculateScale = () => {
  if (!iframeContainer.value) return
  const container = iframeContainer.value
  const containerWidth = container.clientWidth - 40
  const containerHeight = container.clientHeight - 40
  // 如果容器尺寸还是0，跳过（首次渲染时可能为0）
  if (containerWidth <= 0 || containerHeight <= 0) {
    console.log('容器尺寸为0，跳过')
    return
  }
  const scaleX = containerWidth / 1280
  const scaleY = containerHeight / 720
  scale.value = Math.min(scaleX, scaleY, 1)
}

// 计算样式
const scaleStyle = computed(() => {
  return {
    transform: `scale(${scale.value})`,
    transformOrigin: 'center center',
    width: '1280px',
    height: '720px'
  }
})

// iframe加载完成
const onIframeLoad = () => {
  // 刷新scale，确保尺寸正确
  calculateScale()
}

// 监听窗口大小变化
onMounted(() => {
  // 使用ResizeObserver监听容器尺寸变化
  if (iframeContainer.value) {
    const observer = new ResizeObserver(() => {
      calculateScale()
    })
    observer.observe(iframeContainer.value)
    onUnmounted(() => observer.disconnect())
  }
  window.addEventListener('resize', calculateScale)
})

onUnmounted(() => {
  window.removeEventListener('resize', calculateScale)
})

const currentSlidePage = computed(() => store.pages.find(p => p.id === store.currentSlide))
const currentSlideIndex = computed(() => store.pages.findIndex(p => p.id === store.currentSlide))

// 获取当前幻灯片的HTML内容
const currentSlideHtml = computed(() => {
  const currentPage = currentSlidePage.value
  if (!currentPage) return null

  // 从generatedSlides获取当前页的HTML
  const pageNum = currentPage.pageNumber || currentPage.id
  const slide = store.generatedSlides.find(s => s.pageNumber === pageNum)
  return slide ? slide.html : null
})

// 强制刷新key
const iframeKey = ref(0)

// 检查是否有任何生成的幻灯片
const hasGeneratedSlides = computed(() => store.generatedSlides.length > 0)

const currentSlideEvaluation = computed(() => {
  const currentPage = currentSlidePage.value
  if (!currentPage) return null
  const pageNum = currentPage.pageNumber || currentPage.id
  const slide = store.generatedSlides.find(s => s.pageNumber === pageNum)
  return slide?.evaluation || null
})

const currentOverlapText = computed(() => {
  const overlap = currentSlideEvaluation.value?.layout?.overlap_ratio
  if (typeof overlap !== 'number') return 'N/A'
  return `${(overlap * 100).toFixed(2)}%`
})

const currentColorDeviationText = computed(() => {
  const deviation = currentSlideEvaluation.value?.style?.global_color_deviation_percent
  if (typeof deviation !== 'number') return 'N/A'
  return `${deviation.toFixed(1)}%`
})

const evaluationPassRate = computed(() => {
  const slidesWithEval = store.generatedSlides.filter(s => s.evaluation)
  if (slidesWithEval.length === 0) return 'N/A'
  const passedCount = slidesWithEval.filter(s => s.evaluation?.passed).length
  return `${Math.round((passedCount / slidesWithEval.length) * 100)}%`
})

// 获取页面HTML
const getSlideHtml = (pageId) => {
  return store.getSlideHtml(pageId)
}

// 保存PPT到数据库
const savePPT = async () => {
  console.log('[savePPT] 开始保存, generatedSlides数量:', store.generatedSlides.length)
  console.log('[savePPT] currentProject:', store.currentProject)

  if (store.generatedSlides.length === 0) {
    console.log('[savePPT] 没有生成的幻灯片')
    store.showToastMessage('请先生成PPT')
    return
  }

  if (!store.currentProject || !store.currentProject.id) {
    console.log('[savePPT] 没有选中项目')
    store.showToastMessage('请先创建或选择一个项目')
    return
  }

  try {
    const allSlidesHtml = store.generatedSlides.map(slide =>
      `<div class="slide" id="slide-${slide.pageNumber}" data-type="content">\n${slide.html}\n</div>`
    ).join('\n')

    console.log('[savePPT] 发送请求到 /api/ppts')

    const response = await fetch('/api/ppts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: store.currentProject.id,
        outline_id: store.currentOutlineId || null,
        style: store.selectedStyle || 'modern',
        title: store.parseResult?.title || '未命名PPT',
        html_content: allSlidesHtml,
        slide_count: store.generatedSlides.length,
        status: 'completed'
      })
    })

    console.log('[savePPT] 响应状态:', response.status)

    const data = await response.json()
    console.log('[savePPT] 响应数据:', data)

    if (response.ok && data.success) {
      console.log('[savePPT] 保存成功')
      store.totalSlidesCount += store.generatedSlides.length
      store.showToastMessage(`PPT保存成功！共 ${store.generatedSlides.length} 页`)
    } else {
      console.log('[savePPT] 保存失败:', data.error)
      store.showToastMessage(data.error || `保存失败 (${response.status})`)
    }
  } catch (err) {
    console.error('[savePPT] 保存出错:', err)
    store.showToastMessage('保存失败：网络错误')
  }
}

// 下载合并后的PPT
const downloadPPT = () => {
  if (store.generatedSlides.length === 0) {
    store.showToastMessage('请先生成PPT')
    return
  }

  try {
    // 构建幻灯片容器
    const slidesHtml = store.generatedSlides.map(slide =>
      `<div class="slide" id="slide-${slide.pageNumber}" data-type="content">\n            ${slide.html}\n        </div>`
    ).join('\n')

    // 生成完整的HTML文档
    const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${store.parseResult?.title || 'PPT演示文稿'}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 100%; height: 100%; overflow: hidden; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
        .ppt-container { width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; background: #1a1a2e; }
        .slide { display: none; width: 1280px; height: 720px; background: white; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3); position: relative; overflow: hidden; }
        .slide.active { display: block; }
        .navigation { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; z-index: 1000; }
        .nav-btn { padding: 10px 20px; background: rgba(255, 255, 255, 0.9); border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s; }
        .nav-btn:hover { background: white; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2); }
        .nav-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .slide-counter { position: fixed; top: 20px; right: 20px; background: rgba(0, 0, 0, 0.6); color: white; padding: 8px 16px; border-radius: 4px; font-size: 14px; z-index: 1000; }
    </style>
</head>
<body>
    <div class="ppt-container">
${slidesHtml}
    </div>
    <div class="navigation">
        <button class="nav-btn" id="prevBtn" onclick="prevSlide()">上一页</button>
        <button class="nav-btn" id="nextBtn" onclick="nextSlide()">下一页</button>
    </div>
    <div class="slide-counter" id="slideCounter"></div>
    <script>
        let currentSlide = 1;
        const totalSlides = ${store.generatedSlides.length};

        function showSlide(n) {
            if (n < 1) n = 1;
            if (n > totalSlides) n = totalSlides;
            currentSlide = n;
            document.querySelectorAll('.slide').forEach((slide, index) => {
                slide.classList.remove('active');
                if (index + 1 === currentSlide) slide.classList.add('active');
            });
            document.getElementById('prevBtn').disabled = currentSlide === 1;
            document.getElementById('nextBtn').disabled = currentSlide === totalSlides;
            document.getElementById('slideCounter').textContent = currentSlide + ' / ' + totalSlides;
        }

        function nextSlide() { showSlide(currentSlide + 1); }
        function prevSlide() { showSlide(currentSlide - 1); }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') { e.preventDefault(); nextSlide(); }
            else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); prevSlide(); }
            else if (e.key === 'Home') { e.preventDefault(); showSlide(1); }
            else if (e.key === 'End') { e.preventDefault(); showSlide(totalSlides); }
        });

        document.querySelectorAll('.slide').forEach((slide) => {
            slide.addEventListener('click', (e) => { if (!e.target.closest('button')) nextSlide(); });
        });

        showSlide(1);
    <\/script>
</body>
</html>`

    // 创建Blob并下载
    const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${store.parseResult?.title || 'PPT演示文稿'}.html`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    store.showToastMessage('PPT下载成功！')
  } catch (err) {
    console.error('下载PPT失败:', err)
    store.showToastMessage('下载PPT失败')
  }
}

const slideStyle = computed(() => {
  const page = currentSlidePage.value
  if (!page) return {}

  if (page.background) {
    return {
      backgroundImage: `url(${page.background})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center'
    }
  } else if (page.layout === 'cover') {
    return {
      background: 'linear-gradient(135deg, #1e3a5f, #2d5a87)'
    }
  } else {
    return {
      background: '#f8f9fa',
      color: '#1a1a1a'
    }
  }
})

const goToSlide = (slideId) => {
  store.goToSlide(slideId)
}

const prevSlide = () => {
  store.prevSlide()
}

const nextSlide = () => {
  store.nextSlide()
}

// 当有新的幻灯片生成时，强制刷新iframe
watch(() => store.generatedSlides.length, () => {
  iframeLoaded.value = false
  iframeKey.value++
  nextTick(() => nextTick(calculateScale))
})

// 当切换幻灯片时也刷新iframe
watch(() => store.currentSlide, () => {
  // 切换时不设置iframeLoaded，只改变key让iframe重新加载
  iframeKey.value++
}, { immediate: true })
</script>

<style scoped>
/* 生成进度遮罩 */
.generating-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
}

.generating-progress {
  background: rgba(255, 255, 255, 0.95);
  padding: 20px 40px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  text-align: center;
}

.progress-text {
  font-size: 14px;
  color: #333;
  margin-bottom: 12px;
}

.progress-bar {
  width: 200px;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.3s ease;
}

/* iframe容器 - 使用transform缩放 */
.preview-slide-iframe-container {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: visible;
}

.iframe-scale-wrapper {
  /* 固定1280x720原始尺寸 */
  position: relative;
  overflow: visible;
}

.preview-slide-iframe {
  width: 1280px;
  height: 720px;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  background: white;
  display: block;
}

/* 缩略图HTML预览 */
.thumb-html-preview {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #fff;
}

.thumb-iframe {
  width: 200%;
  height: 200%;
  border: none;
  transform: scale(0.5);
  transform-origin: top left;
  pointer-events: none;
}

/* 生成状态指示器 */
.generation-status {
  display: block;
  margin-top: 2px;
}

.generating {
  color: #667eea;
  font-size: 10px;
}

.generated {
  color: #52c41a;
  font-size: 10px;
}

.evaluation-bar {
  display: flex;
  gap: 18px;
  padding: 10px 16px;
  border-top: 1px solid #eef1f6;
  border-bottom: 1px solid #eef1f6;
  background: #fafbff;
}

.evaluation-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.evaluation-label {
  color: #6b7280;
}

.evaluation-value {
  color: #111827;
  font-weight: 600;
}

.evaluation-value.pass {
  color: #16a34a;
}

.evaluation-value.fail {
  color: #d97706;
}
</style>
