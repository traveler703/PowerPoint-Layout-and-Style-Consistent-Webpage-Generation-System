import { reactive, computed } from 'vue'
import { getProjects, createProject, updateProject, deleteProject, createOutline, getOutline, updateOutline, getProjectOutlines, getProjectPPTs, getPPT } from '@/services/api'

// 项目类型图标映射
const typeIcons = {
  business: '📊',
  academic: '🎓',
  vibrant: '🎨',
  tech: '🚀',
  nature: '🌿',
  minimal: '✨'
}

// 项目类型名称映射
const typeNames = {
  business: '商务',
  academic: '学术',
  vibrant: '创意',
  tech: '科技',
  nature: '自然',
  minimal: '个人'
}

// 工作流步骤
const workflowSteps = ['input', 'outline', 'style', 'preview']
const stepTitles = {
  input: '输入文档',
  outline: '编辑大纲',
  style: '应用风格',
  preview: '预览导出'
}

// 全局状态
export const store = reactive({
  // 视图状态
  currentView: 'workspace',

  // 项目列表
  projects: [],

  // 当前项目
  currentProject: null,

  // 工作流步骤
  currentStep: 'input',
  workflowSteps,
  stepTitles,

  // 页面数据
  pages: [],
  currentPageId: null,

  // 预览状态
  currentSlide: 1,

  // 视图模式
  viewMode: 'grid',

  // 右键菜单
  contextMenuProjectId: null,
  showContextMenu: false,
  contextMenuPosition: { x: 0, y: 0 },

  // 模态框
  showNewProjectModal: false,
  showImportModal: false,

  // Toast
  toastMessage: '',
  showToast: false,

  // 统计数据
  totalSlidesCount: 0,

  // 输入状态
  documentText: '',
  inputMode: 'paste',
  charCount: 0,

  // 解析状态
  isParsing: false,
  parseResult: null,

  // 风格选择
  selectedStyle: 'business',

  // 进度
  progressPercent: 0,
  progressText: '准备就绪',

  // PPT生成状态
  isGenerating: false,
  generatedSlides: [],  // 存储生成的幻灯片HTML
  currentGeneratingPage: 0,  // 当前正在生成的页码
  totalPagesToGenerate: 0,   // 总共要生成的页数
  directSlideHtml: null,      // 实验性：直接加载的HTML

  // 大纲状态
  currentOutlineId: null,  // 当前大纲ID

  // 搜索
  searchQuery: '',

  // 加载状态
  loading: false,
  error: null,

  // 初始化 - 从数据库加载数据
  async init() {
    this.loading = true
    this.error = null
    try {
      const response = await getProjects()
      if (response.success) {
        this.projects = response.projects.map(p => ({
          id: p.id,
          name: p.name,
          desc: p.description || '',
          type: p.type || 'business',
          icon: typeIcons[p.type] || typeIcons.business,
          pages: p.page_count || 0,
          updated: p.updated_at ? new Date(p.updated_at).getTime() : Date.now(),
          created: p.created_at ? new Date(p.created_at).getTime() : Date.now()
        }))
      }

      // 加载统计数据
      try {
        const statsRes = await fetch('/api/stats')
        if (statsRes.ok) {
          const statsData = await statsRes.json()
          if (statsData.success) {
            this.totalSlidesCount = statsData.total_slides || 0
          }
        }
      } catch (e) {
        console.log('获取统计数据失败')
      }

      // 实验性：加载slide_1.html
      try {
        const res = await fetch('/output/slide_1.html')
        if (res.ok) {
          this.directSlideHtml = await res.text()
        }
      } catch (e) {
        console.log('slide_1.html not found')
      }
    } catch (err) {
      this.error = '加载项目失败'
      console.error('Load projects error:', err)
    } finally {
      this.loading = false
    }
  },

  // 视图切换
  setView(view) {
    this.currentView = view
  },

  goToWorkspace() {
    this.currentView = 'workspace'
    this.currentProject = null
    this.pages = []
    this.currentPageId = null
  },

  openProject(projectId) {
    this.currentProject = this.projects.find(p => p.id === projectId)
    if (this.currentProject) {
      this.currentView = 'project'
      this.currentStep = 'input'
      this.currentSlide = 1

      // 清空当前数据
      this.pages = []
      this.parseResult = null
      this.documentText = ''

      // 从数据库加载解析结果
      this.loadProjectParseResult(projectId)
    }
  },

  // 加载项目的解析结果 - 从outlines表加载大纲
  async loadProjectParseResult(projectId) {
    try {
      // 1. 先从 projects 表获取原始数据
      const projectResponse = await fetch(`/api/projects/${projectId}`)
      const projectData = await projectResponse.json()

      if (!projectData.success || !projectData.project) {
        console.log('项目不存在')
        return
      }

      // 2. 获取项目的最新大纲
      const outlinesResponse = await fetch(`/api/projects/${projectId}/outlines`)
      const outlinesData = await outlinesResponse.json()

      if (outlinesData.success && outlinesData.outlines && outlinesData.outlines.length > 0) {
        // 使用最新的大纲
        const latestOutline = outlinesData.outlines[0]
        this.currentOutlineId = latestOutline.id

        // 从大纲数据加载页面
        const outlineData = latestOutline.outline_data
        if (outlineData && outlineData.slides) {
          this.pages = outlineData.slides.map((slide, index) => ({
            id: slide.page_number || (Date.now() + index),
            pageNumber: slide.page_number || (index + 1),
            title: slide.title || '未命名页面',
            subtitle: slide.subtitle || '',
            layout: slide.slide_type === 'title' ? 'cover' : 'content',
            bullets: slide.content_points || slide.bullets || [],
            image: null,
            background: null,
            logo: null,
            generatedHtml: null
          }))

          // 构建parseResult（保持兼容性）
          this.parseResult = {
            title: latestOutline.title || projectData.project.name || '未命名文档',
            summary: '',
            sections: outlineData.slides
              .filter(slide => slide.slide_type !== 'title')
              .map(slide => ({
                title: slide.title,
                content: slide.subtitle || '',
                bullets: slide.content_points || slide.bullets || []
              }))
          }

          // 设置当前页面
          if (this.pages.length > 0) {
            this.currentPageId = this.pages[0].id
            this.currentSlide = this.pages[0].id
          }

          console.log('从outlines表加载大纲成功:', this.pages.length, '页')

          // 加载已保存的PPT
          await this.loadSavedPPT(projectId)
          return
        }
      }

      // 3. 如果没有大纲，尝试从 projects.parse_sections 加载（兼容旧数据）
      if (projectData.project.parse_sections) {
        try {
          const sections = typeof projectData.project.parse_sections === 'string'
            ? JSON.parse(projectData.project.parse_sections)
            : projectData.project.parse_sections

          this.parseResult = {
            title: projectData.project.parse_title || projectData.project.name,
            summary: projectData.project.parse_summary || '',
            sections: sections || []
          }

          // 生成页面
          this.generatePagesFromParseResult(this.parseResult)

          // 加载已保存的PPT
          await this.loadSavedPPT(projectId)

          console.log('从projects表加载解析结果（兼容旧数据）')
        } catch (e) {
          console.error('解析parse_sections失败:', e)
        }
      }
    } catch (err) {
      console.error('Load parse result error:', err)
    }
  },

  // 工作流步骤
  setStep(step) {
    this.currentStep = step
  },

  nextStep() {
    const index = this.workflowSteps.indexOf(this.currentStep)
    if (index < this.workflowSteps.length - 1) {
      this.currentStep = this.workflowSteps[index + 1]
    }
  },

  prevStep() {
    const index = this.workflowSteps.indexOf(this.currentStep)
    if (index > 0) {
      this.currentStep = this.workflowSteps[index - 1]
    }
  },

  // 项目管理 - 调用API
  async createProject(name, type) {
    try {
      const response = await createProject({
        name: name || '未命名项目',
        description: '新创建的项目',
        type: type || 'business',
        icon: typeIcons[type] || typeIcons.business
      })

      if (response.success) {
        const newProject = {
          id: response.project_id,
          name: name || '未命名项目',
          desc: '新创建的项目',
          type: type || 'business',
          icon: typeIcons[type] || typeIcons.business,
          pages: 0,
          updated: Date.now(),
          created: Date.now()
        }
        this.projects.unshift(newProject)
        this.showToastMessage('项目创建成功')
        return newProject
      }
    } catch (err) {
      console.error('Create project error:', err)
      this.showToastMessage('创建项目失败')
    }
    return null
  },

  async duplicateProject(projectId) {
    const original = this.projects.find(p => p.id === projectId)
    if (original) {
      return await this.createProject(original.name + ' (副本)', original.type)
    }
    return null
  },

  async deleteProject(projectId) {
    try {
      const response = await deleteProject(projectId)
      if (response.success) {
        const index = this.projects.findIndex(p => p.id === projectId)
        if (index !== -1) {
          this.projects.splice(index, 1)
        }
        this.showToastMessage('项目已删除')
        return true
      }
    } catch (err) {
      console.error('Delete project error:', err)
      this.showToastMessage('删除项目失败')
    }
    return false
  },

  async renameProject(projectId, newName) {
    try {
      const response = await updateProject(projectId, { name: newName })
      if (response.success) {
        const project = this.projects.find(p => p.id === projectId)
        if (project) {
          project.name = newName
          project.updated = Date.now()
        }
        return true
      }
    } catch (err) {
      console.error('Rename project error:', err)
      this.showToastMessage('重命名失败')
    }
    return false
  },

  exportProject(projectId) {
    const project = this.projects.find(p => p.id === projectId)
    return project
  },

  // 页面管理
  selectPage(pageId) {
    this.currentPageId = pageId
  },

  // 大纲管理 - 保存大纲到outlines表（返回boolean表示成功/失败）
  async saveOutlineWithStatus() {
    console.log('[saveOutlineWithStatus] 开始保存, currentProject:', this.currentProject)

    if (!this.currentProject || !this.currentProject.id) {
      console.log('[saveOutlineWithStatus] 没有选中项目')
      this.showToastMessage('请先创建或选择一个项目')
      return false
    }

    try {
      const outlineData = {
        slides: this.pages.map(page => ({
          page_number: page.pageNumber || page.id,
          title: page.title,
          subtitle: page.subtitle || '',
          content_points: page.bullets || [],
          slide_type: page.layout === 'cover' ? 'title' : 'content',
          bullets: page.bullets || []
        }))
      }

      const outlineTitle = this.parseResult?.title || this.currentProject?.name || '未命名大纲'
      console.log('[saveOutlineWithStatus] outlineTitle:', outlineTitle)

      if (this.currentOutlineId) {
        console.log('[saveOutlineWithStatus] 更新现有大纲, id:', this.currentOutlineId)
        const response = await updateOutline(this.currentOutlineId, {
          title: outlineTitle,
          outline_data: outlineData
        })
        console.log('[saveOutlineWithStatus] updateOutline响应:', response)
        if (response.success) {
          this.currentOutlineId = response.outline_id || this.currentOutlineId
          this.showToastMessage('大纲已更新')
          return true
        }
      } else {
        console.log('[saveOutlineWithStatus] 创建新大纲')
        const response = await createOutline({
          project_id: this.currentProject.id,
          title: outlineTitle,
          scenario: 'general',
          audience: '通用受众',
          page_count: this.pages.length,
          outline_data: outlineData
        })
        console.log('[saveOutlineWithStatus] createOutline响应:', response)
        if (response.success) {
          this.currentOutlineId = response.outline_id
          this.showToastMessage('大纲已保存')
          return true
        }
      }
    } catch (err) {
      console.error('[saveOutlineWithStatus] 保存大纲失败:', err)
      this.showToastMessage('保存大纲失败')
    }
    return false
  },

  // 大纲管理 - 保存大纲到outlines表（兼容旧代码）
  async saveOutline() {
    return await this.saveOutlineWithStatus()
  },

  // 从outlines表加载大纲
  async loadOutline(outlineId) {
    try {
      const response = await getOutline(outlineId)
      if (response.success && response.outline) {
        const outline = response.outline
        this.currentOutlineId = outline.id

        // 将大纲数据转换为页面数据
        const outlineData = outline.outline_data
        if (outlineData && outlineData.slides) {
          this.pages = outlineData.slides.map((slide, index) => ({
            id: slide.page_number || (Date.now() + index),
            pageNumber: slide.page_number || (index + 1),
            title: slide.title || '未命名页面',
            subtitle: slide.subtitle || '',
            layout: slide.slide_type === 'title' ? 'cover' : 'content',
            bullets: slide.content_points || slide.bullets || [],
            image: null,
            background: null,
            logo: null,
            generatedHtml: null
          }))

          // 更新parseResult
          this.parseResult = {
            title: outline.title || this.currentProject?.name || '未命名文档',
            summary: '',
            sections: outlineData.slides.map(slide => ({
              title: slide.title,
              content: '',
              bullets: slide.content_points || slide.bullets || []
            }))
          }

          if (this.pages.length > 0) {
            this.currentPageId = this.pages[0].id
            this.currentSlide = this.pages[0].id
          }

          this.showToastMessage('大纲加载成功')
          return true
        }
      }
    } catch (err) {
      console.error('加载大纲失败:', err)
      this.showToastMessage('加载大纲失败')
    }
    return false
  },

  // 加载项目的所有大纲
  async loadProjectOutlines(projectId) {
    try {
      const response = await getProjectOutlines(projectId)
      if (response.success) {
        return response.outlines || []
      }
    } catch (err) {
      console.error('加载项目大纲列表失败:', err)
    }
    return []
  },

  // 从数据库加载已保存的PPT
  async loadSavedPPT(projectId) {
    try {
      const response = await getProjectPPTs(projectId)
      if (response.success && response.ppts && response.ppts.length > 0) {
        const latestPPT = response.ppts[0] // 获取最新保存的PPT

        if (latestPPT.html_content) {
          // 解析保存的HTML内容
          // 格式: <div class="slide" id="slide-1">...content...</div><div class="slide" id="slide-2">...content...</div>
          const slideRegex = /<div class="slide"[^>]*>([\s\S]*?)<\/div>\s*<\/div>\s*<\/div>|<!-- SLIDE_BREAK -->|<\/div>\s*<div class="slide"/g
          let slideMatches = latestPPT.html_content.split(/<div class="slide"/)

          if (slideMatches.length > 1) {
            // 第一个元素是空白的，需要跳过
            this.generatedSlides = slideMatches.slice(1).map((part, index) => {
              // 找到每个slide的结束位置
              const endMatch = part.match(/<\/div>\s*<\/div>\s*<\/div>|<!-- SLIDE_BREAK -->/)
              let html = part
              if (endMatch) {
                html = part.substring(0, part.indexOf(endMatch[0]) + endMatch[0].length)
              }

              // 添加 <div class="slide" 前缀
              html = '<div class="slide"' + html

              return {
                pageNumber: index + 1,
                html: html
              }
            }).filter(slide => slide.html.length > 50) // 过滤掉无效的

            console.log('从数据库加载PPT成功:', this.generatedSlides.length, '页')
            return true
          }
        }
      }
    } catch (err) {
      console.error('加载已保存PPT失败:', err)
    }
    return false
  },

  // 替换完整大纲内容（用于导入整个大纲）
  replaceOutline(outlineData) {
    if (!outlineData || !outlineData.slides) {
      this.showToastMessage('大纲数据无效')
      return false
    }

    this.pages = outlineData.slides.map((slide, index) => ({
      id: slide.page_number || (Date.now() + index),
      pageNumber: slide.page_number || (index + 1),
      title: slide.title || '未命名页面',
      subtitle: slide.subtitle || '',
      layout: slide.slide_type === 'title' ? 'cover' : 'content',
      bullets: slide.content_points || slide.bullets || [],
      image: null,
      background: null,
      logo: null,
      generatedHtml: null
    }))

    // 更新parseResult
    this.parseResult = {
      title: outlineData.title || this.parseResult?.title || '未命名文档',
      summary: outlineData.summary || '',
      sections: outlineData.slides.map(slide => ({
        title: slide.title,
        content: '',
        bullets: slide.content_points || slide.bullets || []
      }))
    }

    if (this.pages.length > 0) {
      this.currentPageId = this.pages[0].id
      this.currentSlide = this.pages[0].id
    }

    this.showToastMessage('大纲已替换')
    return true
  },

  // 更新单个页面的数据
  updatePageData(pageId, updates) {
    const page = this.pages.find(p => p.id === pageId)
    if (page) {
      Object.assign(page, updates)
      // 更新parseResult中的对应section
      if (this.parseResult && this.parseResult.sections) {
        const index = this.pages.findIndex(p => p.id === pageId)
        if (index >= 0 && this.parseResult.sections[index]) {
          this.parseResult.sections[index] = {
            title: page.title,
            content: page.subtitle || '',
            bullets: page.bullets || []
          }
        }
      }
    }
  },

  addPage() {
    const newPage = {
      id: Date.now(),
      title: '新页面',
      subtitle: '',
      layout: 'text',
      image: null,
      background: null,
      logo: null,
      bullets: ['新内容']
    }
    this.pages.push(newPage)
    this.currentPageId = newPage.id
    // 更新页面编号
    this.reindexPages()
    return newPage
  },

  // 重新编号所有页面
  reindexPages() {
    this.pages.forEach((page, index) => {
      page.pageNumber = index + 1
    })
  },

  deletePage(pageId) {
    if (this.pages.length <= 1) return false
    const index = this.pages.findIndex(p => p.id === pageId)
    if (index !== -1) {
      this.pages.splice(index, 1)
      if (this.currentPageId === pageId) {
        this.currentPageId = this.pages[0]?.id
      }
      // 更新页面编号
      this.reindexPages()
      return true
    }
    return false
  },

  duplicatePage(pageId) {
    const page = this.pages.find(p => p.id === pageId)
    if (page) {
      const newPage = {
        ...JSON.parse(JSON.stringify(page)),
        id: Date.now(),
        title: page.title + ' (副本)'
      }
      const index = this.pages.findIndex(p => p.id === pageId)
      this.pages.splice(index + 1, 0, newPage)
      this.currentPageId = newPage.id
      // 更新页面编号
      this.reindexPages()
      return newPage
    }
    return null
  },

  movePage(pageId, direction) {
    const index = this.pages.findIndex(p => p.id === pageId)
    if (index === -1) return false

    if (direction === 'up' && index > 0) {
      [this.pages[index], this.pages[index - 1]] = [this.pages[index - 1], this.pages[index]]
      this.reindexPages()
      return true
    }
    if (direction === 'down' && index < this.pages.length - 1) {
      [this.pages[index], this.pages[index + 1]] = [this.pages[index + 1], this.pages[index]]
      this.reindexPages()
      return true
    }
    return false
  },

  updatePage(pageId, updates) {
    const page = this.pages.find(p => p.id === pageId)
    if (page) {
      Object.assign(page, updates)
    }
  },

  // 解析文档
  async parseDocument() {
    if (!this.documentText || this.documentText.trim().length < 10) {
      this.showToastMessage('请输入足够的文本内容')
      return null
    }

    console.log('开始解析文档...')
    this.isParsing = true
    this.setProgress(0, '正在解析文档...')

    try {
      console.log('发送请求到 /api/parse-text')
      const response = await fetch('/api/parse-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: this.documentText,
          project_id: this.currentProject?.id
        })
      })

      console.log('收到响应:', response.status)
      const data = await response.json()
      console.log('响应数据:', data)

      if (data.success) {
        this.parseResult = data.result
        this.setProgress(50, '正在生成预览...')

        this.setProgress(100, '解析完成')
        this.showToastMessage('文档解析完成，请点击"开始应用"')

        return data.result
      } else {
        this.showToastMessage(data.error || '解析失败')
        return null
      }
    } catch (err) {
      console.error('Parse error:', err)
      this.showToastMessage('解析失败，请重试')
      return null
    } finally {
      this.isParsing = false
    }
  },

  // 从解析结果生成页面
  generatePagesFromParseResult(parseResult) {
    if (!parseResult) return

    this.pages = []
    let pageIndex = 1

    // 生成封面页
    const coverPage = {
      id: Date.now(),
      pageNumber: pageIndex++,
      title: parseResult.title || '未命名文档',
      subtitle: parseResult.summary || '',
      layout: 'cover',
      image: null,
      background: null,
      logo: null,
      bullets: [],
      generatedHtml: null
    }
    this.pages.push(coverPage)

    // 生成内容页
    const sections = parseResult.sections || []
    sections.forEach((section, index) => {
      const page = {
        id: Date.now() + index + 1,
        pageNumber: pageIndex++,
        title: section.title || `第${index + 1}部分`,
        subtitle: '',
        layout: 'content',
        image: null,
        background: null,
        logo: null,
        bullets: section.bullets || [],
        generatedHtml: null
      }
      this.pages.push(page)
    })

    // 设置当前页面
    if (this.pages.length > 0) {
      this.currentPageId = this.pages[0].id
      this.currentSlide = this.pages[0].id
    }

    // 更新项目信息
    if (this.currentProject) {
      this.currentProject.name = parseResult.title || this.currentProject.name
      this.currentProject.pages = this.pages.length

      // 同时更新 projects 数组中的对应项目
      const projectInList = this.projects.find(p => p.id === this.currentProject.id)
      if (projectInList) {
        projectInList.pages = this.pages.length
        projectInList.updated = Date.now()
      }
    }
  },

  // 预览导航
  goToSlide(slideId) {
    this.currentSlide = slideId
  },

  prevSlide() {
    const index = this.pages.findIndex(p => p.id === this.currentSlide)
    if (index > 0) {
      this.currentSlide = this.pages[index - 1].id
    }
  },

  nextSlide() {
    const index = this.pages.findIndex(p => p.id === this.currentSlide)
    if (index < this.pages.length - 1) {
      this.currentSlide = this.pages[index + 1].id
    }
  },

  // 样式
  setStyle(style) {
    this.selectedStyle = style
  },

  // 输入
  setInputMode(mode) {
    this.inputMode = mode
  },

  setDocumentText(text) {
    this.documentText = text
    this.charCount = text.length
  },

  // 视图模式
  setViewMode(mode) {
    this.viewMode = mode
  },

  // 搜索
  setSearchQuery(query) {
    this.searchQuery = query
  },

  // 右键菜单
  showContextMenuAt(x, y, projectId) {
    this.contextMenuPosition = { x, y }
    this.contextMenuProjectId = projectId
    this.showContextMenu = true
  },

  hideContextMenu() {
    this.showContextMenu = false
    this.contextMenuProjectId = null
  },

  // 模态框
  openNewProjectModal() {
    this.showNewProjectModal = true
  },

  closeNewProjectModal() {
    this.showNewProjectModal = false
  },

  openImportModal() {
    this.showImportModal = true
  },

  closeImportModal() {
    this.showImportModal = false
  },

  // Toast
  showToastMessage(message) {
    console.log('[Toast] 显示消息:', message)

    // 清除之前的定时器
    if (this._toastTimer) {
      clearTimeout(this._toastTimer)
    }

    this.toastMessage = message
    this.showToast = true

    // 3秒后隐藏
    this._toastTimer = setTimeout(() => {
      this.showToast = false
      this._toastTimer = null
    }, 3000)
  },

  // 进度
  setProgress(percent, text) {
    this.progressPercent = percent
    if (text) this.progressText = text
  },

  // 设置页面数据（用于打开项目时加载）
  setPages(pages) {
    this.pages = pages
    if (pages.length > 0) {
      this.currentPageId = pages[0].id
      this.currentSlide = pages[0].id
    }
  },

  // 流式生成PPT - 每生成一页就更新预览
  async generatePPTSteam(engine = 'pipeline') {
    if (!this.parseResult) {
      this.showToastMessage('请先解析文档')
      return false
    }

    this.isGenerating = true
    this.generatedSlides = []
    this.currentGeneratingPage = 0
    this.currentStep = 'preview'  // 切换到预览步骤

    // 先保存大纲到数据库
    let outlineId = this.currentOutlineId
    if (!outlineId) {
      outlineId = await this.saveOutline()
    }

    try {
      // 构建大纲数据
      const outline = {
        slides: this.parseResult.sections.map((section, index) => ({
          page_number: index + 2,
          title: section.title,
          content_points: section.bullets || [],
          slide_type: 'content'
        }))
      }

      // 添加封面页
      outline.slides.unshift({
        page_number: 1,
        title: this.parseResult.title || '未命名文档',
        content_points: [],
        slide_type: 'title'
      })

      this.totalPagesToGenerate = outline.slides.length
      this.setProgress(0, `正在生成第1页...`)

      // 调用流式生成接口
      const response = await fetch('/api/generate-ppt-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          outline: outline,
          topic: this.parseResult.title || 'PPT演示文稿',
          scenario: 'general',
          style: this.selectedStyle || 'modern',
          engine
        })
      })

      if (!response.ok) {
        throw new Error('生成请求失败')
      }

      // 使用EventSource接收流式数据
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // 保留未完成的行

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              console.log('[SSE收到]', data.type, 'page_number:', data.page_number, 'html长度:', data.html ? data.html.length : 0)

              if (data.type === 'slide') {
                // 收到一页幻灯片
                console.log('[DEBUG] 更新 currentGeneratingPage:', data.page_number)
                this.currentGeneratingPage = data.page_number
                this.setProgress(
                  Math.round((data.page_number / this.totalPagesToGenerate) * 100),
                  `正在生成第${data.page_number}页...`
                )

                console.log('[DEBUG] 存入generatedSlides, 当前长度:', this.generatedSlides.length)
                // 存储生成的幻灯片HTML
                this.generatedSlides.push({
                  pageNumber: data.page_number,
                  title: data.title,
                  html: data.html,
                  evaluation: data.evaluation || null
                })
                console.log('[DEBUG] 存入后generatedSlides长度:', this.generatedSlides.length)

                // 更新预览页面的HTML
                this.updatePreviewSlide(data.page_number, data.html)

              } else if (data.type === 'error') {
                console.error('生成错误:', data.message)
                this.showToastMessage(`生成第${data.page_number}页失败: ${data.message}`)
              } else if (data.type === 'complete') {
                // 生成完成
                this.setProgress(100, '生成完成')
                this.showToastMessage('PPT生成完成！')
                this.isGenerating = false
              }
            } catch (e) {
              console.error('解析SSE数据失败:', e)
            }
          }
        }
      }

      return true
    } catch (err) {
      console.error('流式生成PPT失败:', err)
      this.showToastMessage('生成PPT失败，请重试')
      this.isGenerating = false
      return false
    }
  },

  // 更新预览幻灯片的HTML内容
  updatePreviewSlide(pageNumber, html) {
    // 找到对应的页面并更新其HTML内容
    const page = this.pages.find(p => p.pageNumber === pageNumber || p.id === pageNumber)
    if (page) {
      page.generatedHtml = html
    }
  },

  // 获取页面生成的HTML
  getSlideHtml(pageNumber) {
    const slide = this.generatedSlides.find(s => s.pageNumber === pageNumber)
    if (!slide) return null

    // 如果html已经包含slide容器，直接返回
    if (slide.html.includes('class="slide"')) {
      return slide.html
    }

    // 否则包装在slide容器中
    return `<div class="slide" id="slide-${slide.pageNumber}" data-type="content">\n${slide.html}\n</div>`
  }
})

// 计算属性
export const filteredProjects = computed(() => {
  const query = store.searchQuery.toLowerCase()
  if (!query) return store.projects
  return store.projects.filter(p =>
    p.name.toLowerCase().includes(query) ||
    p.desc.toLowerCase().includes(query)
  )
})

export const currentPage = computed(() => {
  return store.pages.find(p => p.id === store.currentPageId)
})

export const currentSlidePage = computed(() => {
  return store.pages.find(p => p.id === store.currentSlide)
})

export const currentStepIndex = computed(() => {
  return store.workflowSteps.indexOf(store.currentStep)
})

// 工具函数
export const formatTime = (timestamp) => {
  if (!timestamp) return '未知'
  const date = new Date(timestamp)
  if (isNaN(date.getTime())) return '未知'

  const diff = Date.now() - date.getTime()
  if (diff < 0) return '刚刚更新'

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚更新'
  if (minutes < 60) return `${minutes}分钟前更新`
  if (hours < 24) return `${hours}小时前更新`
  if (days < 7) return `${days}天前更新`
  if (days < 30) return `${Math.floor(days / 7)}周前更新`
  return `${Math.floor(days / 30)}个月前更新`
}

export const getPageIcon = (layout) => {
  const icons = { cover: '📄', title: '📑', 'points-2': '📝', 'points-3': '📋', stat: '📊', 'image-text': '🖼️', text: '📃' }
  return icons[layout] || '📄'
}

export const getLayoutName = (layout) => {
  const names = { cover: '封面版式', title: '标题版式', 'points-2': '双列版式', 'points-3': '三列版式', stat: '数据卡片', 'image-text': '图文版式', text: '纯文版式' }
  return names[layout] || '标准版式'
}

export { typeIcons, typeNames }
