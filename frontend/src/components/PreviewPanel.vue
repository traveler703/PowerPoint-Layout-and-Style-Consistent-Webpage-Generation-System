<template>
  <div class="preview-container">
    <!-- Left: Page Thumbnails -->
    <div class="preview-pages-panel">
      <div class="preview-pages-header">
        <h4>所有页面</h4>
        <span class="page-count">{{ previewPages.length }} 页</span>
      </div>
      <div class="preview-pages-body">
        <div
          v-for="(page, index) in previewPages"
          :key="page.id"
          class="preview-page-thumb"
          :class="{ active: store.currentSlide === page.id }"
          @click="goToSlide(page.id)"
        >
          <div class="preview-page-thumb-preview" :class="{ 'layout-content': page.layout === 'content' }" :ref="el => setThumbRef(el, page.id)">
            <!-- 如果有生成的HTML，显示缩略图预览 -->
            <div v-if="getThumbnailSlideHtml(page.pageNumber || page.id)" class="thumb-html-preview">
              <iframe
                :srcdoc="getThumbnailSlideHtml(page.pageNumber || page.id)"
                class="thumb-iframe"
                sandbox="allow-same-origin allow-scripts"
                @load="calculateThumbScale"
              ></iframe>
            </div>
            <img v-else-if="page.image" :src="page.image" alt="">
            <span v-else>{{ getPageIcon(page.layout) }}</span>
          </div>
          <div class="preview-page-thumb-info">
            <span class="preview-page-thumb-title">{{ page.title }}</span>
            <span class="preview-page-thumb-num">{{ index + 1 }}/{{ previewPages.length }}</span>
            <!-- 生成状态指示器 -->
            <span v-if="store.isGenerating && (page.id === store.currentGeneratingPage || store.currentGeneratingPage > index + 1)" class="generation-status">
              <span v-if="store.currentGeneratingPage === index + 1" class="generating">生成中...</span>
              <span v-else-if="store.currentGeneratingPage > index + 1" class="generated">✓</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="preview-workspace">
    <!-- Center: Main Preview -->
    <div class="preview-main-panel">
      <div class="preview-main-header">
        <span style="font-size: 14px; font-weight: 600;">
          第 {{ currentSlideIndex + 1 }} 页 / {{ previewPages.length }} 页
        </span>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-ghost" style="padding: 6px 12px; font-size: 12px;" @click="prevSlide" :disabled="currentSlideIndex === 0">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
            上一页
          </button>
          <button class="btn btn-ghost" style="padding: 6px 12px; font-size: 12px;" @click="nextSlide" :disabled="currentSlideIndex === previewPages.length - 1">
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
        <div v-if="currentSlideHtml" class="preview-slide-frame-container">
          <div class="preview-slide-frame-wrapper">
            <iframe
              ref="slideIframe"
              :key="iframeKey"
              :srcdoc="currentSlideHtml"
              class="preview-slide-frame"
              sandbox="allow-same-origin allow-scripts"
              @load="handleMainFrameLoad"
            ></iframe>
          </div>
        </div>

        <!-- 否则显示默认预览 -->
        <div
          v-else
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

    <aside class="preview-ai-panel">
      <div class="preview-ai-header">
        <h4>AI 页面修改</h4>
        <span>选择页面后输入修改指令</span>
      </div>
      <div class="preview-ai-messages">
        <div v-if="revisionMessages.length === 0" class="preview-ai-empty">
          可以针对单页做局部调整，例如“把标题字号调大一点”。
        </div>
        <div
          v-for="message in revisionMessages"
          :key="message.id"
          class="preview-ai-message"
        >
          {{ message.text }}
        </div>
      </div>
      <div class="preview-ai-controls">
        <select v-model="revisionTargetPageId" class="preview-ai-select">
          <option value="">选择页面</option>
          <option
            v-for="(page, index) in previewPages"
            :key="page.id"
            :value="page.id"
          >
            第 {{ index + 1 }} 页：{{ page.title || '未命名页面' }}
          </option>
        </select>
        <textarea
          v-model="revisionInput"
          class="preview-ai-input"
          placeholder="输入修改要求"
          @keydown.enter.exact.prevent="sendRevisionMessage"
        ></textarea>
        <button
          class="btn btn-primary"
          :disabled="!revisionInput.trim() || isRewriting"
          @click="sendRevisionMessage"
        >
          {{ isRewriting ? '修改中...' : '发送' }}
        </button>
      </div>
    </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { store, getPageIcon } from '../stores/appStore'
import { rewriteSlide } from '../services/api'

const slideIframe = ref(null)
const iframeKey = ref(0)
const revisionInput = ref('')
const revisionTargetPageId = ref('')
const revisionMessages = ref([])
const isRewriting = ref(false)
const rewrittenSlideHtmlMap = ref({})

const previewPages = computed(() => {
  if (store.generatedSlides.length > 0 || store.isGenerating) {
    const generatedByPage = new Map(store.generatedSlides.map(slide => [slide.pageNumber, slide]))
    const total = Math.max(
      store.totalPagesToGenerate || 0,
      store.pages.length || 0,
      store.generatedSlides.length || 0
    )
    return Array.from({ length: total }, (_, index) => {
      const pageNumber = index + 1
      const slide = generatedByPage.get(pageNumber)
      const sourcePage = store.pages[index] || {}
      return {
        id: pageNumber,
        pageNumber,
        title: slide?.title || sourcePage.title || `第 ${pageNumber} 页`,
        layout: slide?.pageType || sourcePage.layout || 'content',
        bullets: sourcePage.bullets || []
      }
    })
  }
  return store.pages
})

// 缩略图缩放计算
const thumbRefs = ref({})

const calculateThumbScale = () => {
  // 等待DOM更新
  nextTick(() => {
    Object.values(thumbRefs.value).forEach(container => {
      if (container) {
        const iframe = container.querySelector('.thumb-iframe')
        if (iframe) {
          const containerWidth = container.offsetWidth
          const containerHeight = container.offsetHeight
          // 计算缩放比例（保持16:9）
          const scaleX = containerWidth / 1280
          const scaleY = containerHeight / 720
          const scale = Math.min(scaleX, scaleY)
          iframe.style.transform = `scale(${scale})`
        }
      }
    })
  })
}

const setThumbRef = (el, pageId) => {
  if (el) {
    thumbRefs.value[pageId] = el
  }
}

// 主预览框scale计算
const calculateMainScale = () => {
  nextTick(() => {
    const wrapper = document.querySelector('.preview-slide-frame-wrapper')
    if (wrapper) {
      const parent = wrapper.parentElement
      const parentWidth = parent.clientWidth
      const parentHeight = parent.clientHeight

      const scaleX = parentWidth / 1280
      const scaleY = parentHeight / 720
      const scale = Math.min(scaleX, scaleY)

      wrapper.style.transform = `scale(${scale})`
    }
  })
}

const handleResize = () => {
  calculateThumbScale()
  calculateMainScale()
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

watch(
  () => [
    previewPages.value.length,
    store.generatedSlides.length,
    Boolean(store.directSlideHtml),
    store.currentStep,
  ],
  () => setTimeout(calculateThumbScale, 50),
  { flush: 'post' }
)

const currentSlidePage = computed(() => previewPages.value.find(p => p.id === store.currentSlide) || previewPages.value[0])
const currentSlideIndex = computed(() => Math.max(previewPages.value.findIndex(p => p.id === store.currentSlide), 0))

// 当前幻灯片的HTML内容
const currentSlideHtml = computed(() => {
  const currentPage = currentSlidePage.value
  if (!currentPage) return null
  const pageNum = currentPage.pageNumber || currentPage.id
  // AI 修改后的 HTML 会写回 generatedSlides；主预览和缩略图统一走同一套单页包装逻辑。
  return getSlideHtml(pageNum)
    || (rewrittenSlideHtmlMap.value[pageNum] ? injectOverflowLock(rewrittenSlideHtmlMap.value[pageNum]) : null)
    || buildSlideDocumentFromPresentation(store.directSlideHtml, currentSlideIndex.value)
})

// 当切换幻灯片时刷新iframe
watch(() => store.currentSlide, () => {
  if (store.directSlideHtml) {
    syncPresentationFrame()
  } else {
    iframeKey.value++
  }
  setTimeout(calculateMainScale, 50)
}, { immediate: true })

watch(() => store.directSlideHtml, () => {
  iframeKey.value++
  setTimeout(() => {
    calculateMainScale()
    syncPresentationFrame()
  }, 50)
})

// 获取当前幻灯片的页面URL
const currentSlideUrl = computed(() => {
  const currentPage = currentSlidePage.value
  if (!currentPage) return null

  // 从generatedSlides获取当前页的URL
  const pageNum = currentPage.pageNumber || currentPage.id
  const slide = store.generatedSlides.find(s => s.pageNumber === pageNum)
  return slide?.pageUrl || null
})

// 检查是否有任何生成的幻灯片
const hasGeneratedSlides = computed(() => store.generatedSlides.length > 0 || Boolean(store.directSlideHtml))

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

// 获取页面HTML - 处理内联固定尺寸样式
const getSlideHtml = (pageId) => {
  const html = store.getSlideHtml(pageId)
  if (!html) return null
  // 注入样式强制禁止内部滚动
  return injectOverflowLock(html)
}

const getThumbnailSlideHtml = (pageId) => {
  const html = getSlideHtml(pageId)
  if (html) return html
  if (!store.directSlideHtml) return null
  const slideIndex = Math.max(previewPages.value.findIndex(page => String(page.id) === String(pageId)), 0)
  return buildSlideDocumentFromPresentation(store.directSlideHtml, slideIndex, true)
}

watch(revisionTargetPageId, () => {
  const targetPage = previewPages.value.find(page => String(page.id) === String(revisionTargetPageId.value))
  if (targetPage) store.goToSlide(targetPage.id)
})

function buildPagePayload(page) {
  const pageNumber = page.pageNumber || page.id
  const slide = store.generatedSlides.find(s => s.pageNumber === pageNumber)
  return {
    id: page.id,
    page_number: pageNumber,
    title: page.title || '',
    subtitle: page.subtitle || '',
    layout: page.layout || '',
    bullets: page.bullets || [],
    html: rewrittenSlideHtmlMap.value[pageNumber] || slide?.html || ''
  }
}

function applyRewriteResult(response) {
  const result = response.result || response
  const pageId = result.page_id ?? revisionTargetPageId.value
  const pageData = response.page_data || result.page_data || {}
  const pageNumber = Number(pageData.page_number || pageData.pageNumber || pageId)
  const pageIndex = store.pages.findIndex(page => Number(page.pageNumber || page.id) === pageNumber)
  if (pageIndex >= 0) {
    Object.assign(store.pages[pageIndex], pageData)
  }
  if (response.html) {
    rewrittenSlideHtmlMap.value[pageNumber] = response.html
    const slideIndex = store.generatedSlides.findIndex(s => s.pageNumber === pageNumber)
    if (slideIndex >= 0) {
      store.generatedSlides.splice(slideIndex, 1, {
        ...store.generatedSlides[slideIndex],
        title: pageData.title || store.generatedSlides[slideIndex].title,
        html: response.html
      })
    } else {
      store.generatedSlides.push({
        pageNumber,
        pageType: pageData.layout || 'content',
        title: pageData.title || '',
        html: response.html
      })
    }
  }
  if (response.presentation_html) {
    store.directSlideHtml = response.presentation_html
  }
  if (response.output_path) {
    store.presentationOutputPath = response.output_path
  }
  iframeKey.value++
  nextTick(calculateMainScale)
}

async function sendRevisionMessage() {
  const text = revisionInput.value.trim()
  if (!text || isRewriting.value) return

  const targetPage = previewPages.value.find(page => String(page.id) === String(revisionTargetPageId.value))
  if (!targetPage) {
    store.showToastMessage('请先选择要修改的页面')
    return
  }

  store.goToSlide(targetPage.id)
  revisionMessages.value.push({
    id: Date.now(),
    text: `第 ${previewPages.value.indexOf(targetPage) + 1} 页：${text}`
  })

  isRewriting.value = true
  try {
    const response = await rewriteSlide({
      project_id: store.currentProject?.id || null,
      output_path: store.presentationOutputPath || null,
      page: buildPagePayload(targetPage),
      instruction: text
    })
    if (response.success) {
      applyRewriteResult(response)
      store.showToastMessage('页面已更新')
    } else {
      store.showToastMessage(response.error || '页面修改失败')
    }
  } catch (err) {
    console.error('修改页面失败:', err)
    store.showToastMessage(err?.response?.data?.error || '页面修改失败')
  } finally {
    isRewriting.value = false
    revisionInput.value = ''
  }
}

// 注入样式强制禁止内部滚动
function injectOverflowLock(html) {
  const overflowCss = '*{overflow:hidden!important}html,body{overflow:hidden!important;height:100%!important;margin:0!important;padding:0!important}'
  
  if (html.includes('<style')) {
    html = html.replace(/(<style[^>]*>)/i, '$1\n' + overflowCss)
  } else if (html.includes('</head>')) {
    html = html.replace('</head>', `<style>${overflowCss}</style></head>`)
  } else {
    html = `<style>${overflowCss}</style>` + html
  }
  return html
}

function syncPresentationFrame() {
  if (!store.directSlideHtml) return
  const pageNum = currentSlidePage.value?.pageNumber || currentSlidePage.value?.id
  if (store.generatedSlides.some(slide => slide.pageNumber === pageNum && slide.html)) return

  setTimeout(() => {
    const frameWindow = slideIframe.value?.contentWindow
    const slideIndex = Math.max(currentSlideIndex.value, 0)
    if (frameWindow && typeof frameWindow.goToSlide === 'function') {
      frameWindow.goToSlide(slideIndex)
    }
  }, 0)
}

function handleMainFrameLoad() {
  syncPresentationFrame()
  calculateMainScale()
}

function buildSlideDocumentFromPresentation(html, slideIndex, forThumbnail = false) {
  if (!html) return null
  const viewportCss = `
    <style>
      html, body {
        width: 1280px !important;
        height: 720px !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        background: transparent !important;
      }
      .slides-wrapper,
      .slides-track,
      .slide,
      .slide-container,
      .slide-wrapper {
        width: 1280px !important;
        height: 720px !important;
        min-width: 1280px !important;
        min-height: 720px !important;
        max-width: 1280px !important;
        max-height: 720px !important;
        overflow: hidden !important;
      }
      .nav-dots,
      .slide-nav,
      .navigation,
      .controls {
        display: none !important;
      }
    </style>
  `

  try {
    const doc = new DOMParser().parseFromString(html, 'text/html')
    const track = doc.querySelector('#slidesTrack, .slides-track')
    const slides = track
      ? Array.from(track.children).filter(child => child.classList?.contains('slide-container') || child.classList?.contains('slide'))
      : []
    const selected = slides[Math.max(0, Math.min(slideIndex, slides.length - 1))]

    if (track && selected) {
      const clone = selected.cloneNode(true)
      track.innerHTML = ''
      track.appendChild(clone)
      track.style.transform = 'translateX(0)'
      track.style.width = '1280px'
    }

    doc.querySelectorAll('.nav-dots, .slide-nav, .navigation, .controls, .nav-arrows, .page-indicator').forEach(el => {
      el.style.display = 'none'
    })

    const style = doc.createElement('style')
    style.textContent = viewportCss.replace(/<\/?style>/g, '')
    doc.head.appendChild(style)

    const scripts = doc.querySelectorAll('script')
    scripts.forEach(script => script.remove())

    return '<!DOCTYPE html>\n' + doc.documentElement.outerHTML
  } catch (e) {
    console.warn('构建单页预览失败，回退完整HTML:', e)
    if (html.includes('</head>')) {
      return html.replace('</head>', `${viewportCss}</head>`)
    }
    return `${viewportCss}${html}`
  }
}

// 清理HTML内联样式中的固定尺寸，使其能正确缩放
function cleanInlineStyles(html) {
  let cleaned = html

  // 精确匹配这些属性及其值
  const sizeProps = ['width', 'height', 'max-width', 'min-width', 'max-height', 'min-height']

  sizeProps.forEach(prop => {
    // 精确匹配: 属性名后跟冒号、数字、px
    // 例如: width:100px; 或 width: 100px; 或 width:100px
    const regex = new RegExp(`${prop}[\\s]*:[\\s]*\\d+px[\\s]*;?`, 'gi')
    cleaned = cleaned.replace(regex, (match) => {
      // 如果原来有分号结尾，保留一个分号
      return match.endsWith(';') ? ';' : ''
    })
  })

  // 清理空的分号
  cleaned = cleaned.replace(/;(\s*")/g, '$1')

  // 移除只有分号的style属性
  cleaned = cleaned.replace(/style="\s*;?\s*"/g, '')

  return cleaned
}

// 保存PPT到数据库
const savePPT = async () => {
  console.log('[savePPT] 开始保存, generatedSlides数量:', store.generatedSlides.length)
  console.log('[savePPT] currentProject:', store.currentProject)

  if (store.generatedSlides.length === 0 && !store.directSlideHtml) {
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
    const htmlContent = store.directSlideHtml || store.generatedSlides.map(slide =>
      `<div class="slide" id="slide-${slide.pageNumber}" data-type="content">\n${slide.html}\n</div>`
    ).join('\n')
    const slideCount = store.generatedSlides.length || store.totalSlidesCount || 1

    console.log('[savePPT] 发送请求到 /api/ppts')

    const response = await fetch('/api/ppts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: store.currentProject.id,
        outline_id: store.currentOutlineId || null,
        style: store.selectedStyle || 'modern',
        title: store.parseResult?.title || '未命名PPT',
        html_content: htmlContent,
        slide_count: slideCount,
        status: 'completed'
      })
    })

    console.log('[savePPT] 响应状态:', response.status)

    const data = await response.json()
    console.log('[savePPT] 响应数据:', data)

    if (response.ok && data.success) {
      console.log('[savePPT] 保存成功')
      store.totalSlidesCount += slideCount
      store.showToastMessage(`PPT保存成功！共 ${slideCount} 页`)
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
  if (store.generatedSlides.length === 0 && !store.directSlideHtml) {
    store.showToastMessage('请先生成PPT')
    return
  }

  try {
    const title = store.parseResult?.title || 'PPT演示文稿'
    if (store.directSlideHtml) {
      downloadHtml(store.directSlideHtml, getDownloadFilename(title))
      store.showToastMessage('PPT下载成功！')
      return
    }

    const slideDocuments = store.generatedSlides.map((slide) => {
      const raw = String(slide.html || '')
      if (/<\s*!doctype|<\s*html/i.test(raw)) {
        return raw
      }
      return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    html, body { margin: 0; padding: 0; width: 1280px; height: 720px; overflow: hidden; background: #ffffff; }
  </style>
</head>
<body>${raw}</body>
</html>`
    })

    // 使用 iframe + srcdoc 切页，避免把完整 HTML 再嵌入 div 导致乱码/解析错乱
    const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 100%; height: 100%; overflow: hidden; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #1a1a2e; }
        .ppt-container { width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
        .slide-frame {
            width: 1280px;
            height: 720px;
            border: none;
            background: #fff;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        .navigation { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; z-index: 1000; }
        .nav-btn { padding: 10px 20px; background: rgba(255, 255, 255, 0.9); border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: all 0.3s; }
        .nav-btn:hover { background: white; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2); }
        .nav-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .slide-counter { position: fixed; top: 20px; right: 20px; background: rgba(0, 0, 0, 0.6); color: white; padding: 8px 16px; border-radius: 4px; font-size: 14px; z-index: 1000; }
    </style>
</head>
<body>
    <div class="ppt-container">
        <iframe id="slideFrame" class="slide-frame" sandbox="allow-same-origin allow-scripts"></iframe>
    </div>
    <div class="navigation">
        <button class="nav-btn" id="prevBtn" onclick="prevSlide()">上一页</button>
        <button class="nav-btn" id="nextBtn" onclick="nextSlide()">下一页</button>
    </div>
    <div class="slide-counter" id="slideCounter"></div>
    <script>
        let currentSlide = 1;
        const slides = ${JSON.stringify(slideDocuments).replace(/<\//g, '<\\/')};
        const totalSlides = slides.length;
        const frame = document.getElementById('slideFrame');

        function showSlide(n) {
            if (n < 1) n = 1;
            if (n > totalSlides) n = totalSlides;
            currentSlide = n;
            frame.srcdoc = slides[currentSlide - 1] || '';
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

        showSlide(1);
    <\/script>
</body>
</html>`

    downloadHtml(fullHtml, getDownloadFilename(title))

    store.showToastMessage('PPT下载成功！')
  } catch (err) {
    console.error('下载PPT失败:', err)
    store.showToastMessage('下载PPT失败')
  }
}

function downloadHtml(html, filename) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function getDownloadFilename(fallbackTitle) {
  const outputPath = store.presentationOutputPath || ''
  const outputName = outputPath.split(/[\\/]/).filter(Boolean).pop()
  if (outputName && outputName.toLowerCase().endsWith('.html')) {
    return outputName
  }
  return `${fallbackTitle}.html`
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
  if (currentSlideIndex.value > 0) {
    store.goToSlide(previewPages.value[currentSlideIndex.value - 1].id)
  }
}

const nextSlide = () => {
  if (currentSlideIndex.value < previewPages.value.length - 1) {
    store.goToSlide(previewPages.value[currentSlideIndex.value + 1].id)
  }
}
</script>

<style scoped>
.preview-workspace {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
}

.preview-ai-panel {
  min-width: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(129, 140, 248, 0.18);
  border-radius: 10px;
  background: #0f1118;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
  overflow: hidden;
}

.preview-ai-header {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  background: #151826;
}

.preview-ai-header h4 {
  margin: 0 0 4px;
  font-size: 14px;
  color: #f8fafc;
}

.preview-ai-header span {
  font-size: 12px;
  color: #9ca3af;
}

.preview-ai-messages {
  flex: 1;
  min-height: 0;
  padding: 12px;
  overflow: auto;
}

.preview-ai-empty,
.preview-ai-message {
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
}

.preview-ai-empty {
  color: #aeb8cc;
  background: rgba(255,255,255,0.05);
}

.preview-ai-message {
  margin-bottom: 8px;
  color: #e5e7eb;
  background: rgba(99, 102, 241, 0.16);
  border: 1px solid rgba(129, 140, 248, 0.22);
}

.preview-ai-controls {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid rgba(255,255,255,0.08);
  background: #111421;
}

.preview-ai-select,
.preview-ai-input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 8px;
  font-size: 12px;
  color: #f8fafc;
  background: #0b0d14;
}

.preview-ai-input::placeholder {
  color: #64748b;
}

.preview-ai-select {
  height: 34px;
  padding: 0 10px;
}

.preview-ai-input {
  min-height: 84px;
  padding: 10px;
  resize: vertical;
}

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

/* iframe容器 - 背景容器 */
.preview-slide-frame-container {
  width: 100%;
  height: 100%;
  background: #0a0c14;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  position: relative;
}

/* 缩放器 - 使用transform-origin和scale实现完美缩放 */
.preview-slide-frame-wrapper {
  width: 1280px;
  height: 720px;
  transform-origin: center center;
  transition: transform 0.15s ease;
}

.preview-slide-frame {
  width: 1280px;
  height: 720px;
  border: none;
  overflow: hidden;
  background: white;
}

/* 缩略图HTML预览 - 保持16:9比例 */
.preview-page-thumb-preview.layout-content {
  aspect-ratio: 16 / 9;
  height: auto;
}

.thumb-html-preview {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #fff;
  position: relative;
  border-radius: 4px;
}

.thumb-iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 1280px;
  height: 720px;
  border: none;
  transform-origin: top left;
  pointer-events: none;
  /* 动态计算缩放比例，通过JS设置 */
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
