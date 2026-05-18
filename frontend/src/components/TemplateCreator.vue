<template>
  <div class="creator-view">
    <!-- Header -->
    <header class="creator-header">
      <div class="creator-header-left">
        <button class="btn btn-ghost" @click="goBack">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          返回模板
        </button>
        <div class="creator-title">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          AI 模板创建器
        </div>
      </div>
      <div class="creator-header-right">
        <button class="btn btn-secondary" @click="resetAll" :disabled="messages.length === 0">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          重置对话
        </button>
        <button class="btn btn-primary" @click="saveTemplate" :disabled="!hasValidTemplate">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>
          </svg>
          保存模板
        </button>
      </div>
    </header>

    <!-- Main Layout -->
    <main class="creator-main">
      <!-- Left: AI Chat Panel -->
      <section class="panel panel-chat">
        <div class="panel-header">
          <div class="panel-title">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
            AI 对话
          </div>
          <div class="panel-actions">
            <button class="icon-btn" @click="toggleAutoScroll" :class="{ active: autoScroll }" title="自动滚动">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Chat Messages -->
        <div class="chat-messages" ref="chatContainer">
          <!-- Welcome Message -->
          <div v-if="messages.length === 0" class="chat-welcome">
            <div class="welcome-orb">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
              </svg>
            </div>
            <h3>告诉 AI 你想要的模板风格</h3>
            <p>用自然语言描述你的模板需求，AI 会帮你生成完整的模板配置。你也可以直接编辑右侧的配置面板。</p>
            <div class="quick-prompts">
              <button class="quick-prompt" @click="sendQuickPrompt('设计一个商务风格的PPT模板，配色以深蓝色为主，内容页简洁大气')">
                <span class="qp-icon">💼</span> 商务风格
              </button>
              <button class="quick-prompt" @click="sendQuickPrompt('创建一个科技感十足的模板，适合技术演示，使用霓虹光效和赛博朋克风格')">
                <span class="qp-icon">🚀</span> 科技风格
              </button>
              <button class="quick-prompt" @click="sendQuickPrompt('设计一个清新文艺的模板，适合文学、诗词展示，使用淡雅的水墨风格')">
                <span class="qp-icon">🖌️</span> 文艺风格
              </button>
              <button class="quick-prompt" @click="sendQuickPrompt('创建一个儿童教育风格的模板，活泼可爱，色彩明亮，适合幼儿教学内容')">
                <span class="qp-icon">🎨</span> 儿童风格
              </button>
            </div>
          </div>

          <!-- Messages -->
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message"
            :class="msg.role"
          >
            <div class="message-avatar">
              <div v-if="msg.role === 'user'" class="avatar user">U</div>
              <div v-else class="avatar ai">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
              </div>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-role">{{ msg.role === 'user' ? '你' : 'AI 助手' }}</span>
                <span class="message-time">{{ msg.time }}</span>
              </div>
              <div class="message-body" v-html="renderMarkdown(msg.content)"></div>
              <div v-if="msg.role === 'assistant' && msg.llmResponse?.parsed" class="message-template-preview">
                <div class="mtp-label">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  模板「{{ msg.llmResponse.parsed.template_name || '自定义' }}」已生成
                </div>
                <div class="mtp-meta">
                  <span class="mtp-tag" v-for="tag in (msg.llmResponse.parsed.tags || []).slice(0, 4)" :key="tag">{{ tag }}</span>
                  <span class="mtp-pages">{{ Object.keys(msg.llmResponse.parsed.page_types || {}).length }} 种页面类型</span>
                </div>
                <div class="mtp-actions">
                  <button class="mini-btn" @click="msg.showFull = !msg.showFull">
                    {{ msg.showFull ? '收起配置' : '查看完整配置' }}
                  </button>
                </div>
                <pre v-if="msg.showFull" class="mtp-code">{{ formatJson(msg.llmResponse.parsed) }}</pre>
              </div>
            </div>
          </div>

          <!-- Typing Indicator -->
          <div v-if="isTyping" class="message assistant">
            <div class="message-avatar">
              <div class="avatar ai">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
                </svg>
              </div>
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Input Area -->
        <div class="chat-input-area">
          <div class="input-hints" v-if="messages.length === 0">
            <span class="input-hint-label">提示词建议：</span>
            <span class="input-hint" @click="userInput = '帮我设计一个简洁的商务模板，主色调是深蓝色'">简洁商务</span>
            <span class="input-hint" @click="userInput = '科技风格的PPT模板，要有赛博朋克感'">赛博朋克</span>
            <span class="input-hint" @click="userInput = '水墨中国风的模板设计'">水墨风</span>
          </div>
          <div class="input-row">
            <textarea
              ref="inputRef"
              class="chat-input"
              v-model="userInput"
              placeholder="描述你想要的设计风格..."
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.enter.shift.exact="userInput += '\n'"
              rows="1"
            ></textarea>
            <button
              class="send-btn"
              @click="sendMessage"
              :disabled="!userInput.trim() || isTyping"
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
              </svg>
            </button>
          </div>
          <div class="input-meta">
            <span>Enter 发送 · Shift+Enter 换行</span>
            <span v-if="currentModel">使用模型: {{ currentModel }}</span>
          </div>
        </div>
      </section>

      <!-- Center: Live Preview Panel -->
      <section class="panel panel-preview">
        <div class="panel-header">
          <div class="panel-title">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
            实时预览
          </div>
          <div class="panel-actions">
            <button class="icon-btn" :class="{ active: previewScale === 'fit' }" @click="previewScale = 'fit'" title="适应窗口">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
              </svg>
            </button>
            <button class="icon-btn" :class="{ active: previewScale === '100' }" @click="previewScale = '100'" title="100%">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"/>
              </svg>
            </button>
            <button class="icon-btn" @click="openFullscreen" title="全屏预览">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
              </svg>
            </button>
          </div>
        </div>

        <div class="preview-container" :class="previewScale">
          <iframe
            ref="previewFrame"
            class="preview-frame"
            :srcdoc="previewHtml"
            sandbox="allow-scripts"
            @load="onPreviewLoad"
          ></iframe>
        </div>

        <!-- Slide Thumbnails -->
        <div class="preview-slides" v-if="previewSlides.length > 0">
          <div
            v-for="(slide, idx) in previewSlides"
            :key="idx"
            class="slide-thumb"
            :class="{ active: activeSlide === idx }"
            @click="selectSlide(idx)"
          >
            <div class="thumb-inner" :style="{ background: getSlideThumbStyle(slide) }">
              <div class="thumb-number">{{ idx + 1 }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Right: Structured Config Panel -->
      <section class="panel panel-config">
        <div class="panel-header">
          <div class="panel-title">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            模板配置
          </div>
          <div class="panel-actions">
            <button class="icon-btn" @click="toggleJsonView" :class="{ active: showJson }" title="JSON 视图">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- JSON View -->
        <div v-if="showJson" class="config-json">
          <textarea
            class="json-editor"
            v-model="jsonEditorContent"
            @change="applyJsonEdit"
            spellcheck="false"
          ></textarea>
          <button class="btn btn-primary btn-sm" @click="applyJsonEdit" style="margin-top: 8px; width: 100%;">
            应用 JSON
          </button>
        </div>

        <!-- Structured Config -->
        <div v-else class="config-sections">
          <!-- Basic Info -->
          <div class="config-section">
            <div class="config-section-header" @click="toggleSection('basic')">
              <span>基本信息</span>
              <svg :class="{ rotated: !collapsedSections.basic }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>
            <div class="config-section-body" v-show="!collapsedSections.basic">
              <div class="form-group">
                <label>模板 ID</label>
                <input class="form-input" v-model="config.template_id" placeholder="my_template">
              </div>
              <div class="form-group">
                <label>模板名称</label>
                <input class="form-input" v-model="config.template_name" placeholder="我的模板">
              </div>
              <div class="form-group">
                <label>描述</label>
                <textarea class="form-textarea" v-model="config.description" placeholder="模板描述..." rows="2"></textarea>
              </div>
              <div class="form-group">
                <label>标签 (逗号分隔)</label>
                <input class="form-input" v-model="tagsString" @change="syncTags" placeholder="科技, 深色, 未来">
              </div>
            </div>
          </div>

          <!-- Colors -->
          <div class="config-section">
            <div class="config-section-header" @click="toggleSection('colors')">
              <span>配色方案</span>
              <svg :class="{ rotated: !collapsedSections.colors }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>
            <div class="config-section-body" v-show="!collapsedSections.colors">
              <div class="color-grid">
                <div v-for="(val, key) in config.css_variables" :key="key" class="color-item">
                  <div class="color-preview" :style="{ background: resolveColor(val) }"></div>
                  <div class="color-info">
                    <span class="color-key">{{ key }}</span>
                    <input
                      class="color-value"
                      :value="val"
                      @change="updateCssVar(key, $event.target.value)"
                    >
                  </div>
                  <button class="color-delete" @click="removeCssVar(key)" title="删除">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              </div>
              <button class="add-color-btn" @click="showAddColor = true">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
                添加颜色变量
              </button>
              <!-- Color Palette Generator -->
              <div class="palette-section">
                <div class="palette-label">快速配色</div>
                <div class="palette-presets">
                  <button class="palette-preset" v-for="p in colorPresets" :key="p.name" @click="applyPalette(p)" :title="p.name">
                    <div class="palette-swatches">
                      <div v-for="c in p.colors" :key="c" :style="{ background: c }"></div>
                    </div>
                    <span>{{ p.name }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Page Types -->
          <div class="config-section">
            <div class="config-section-header" @click="toggleSection('pages')">
              <span>页面类型</span>
              <svg :class="{ rotated: !collapsedSections.pages }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>
            <div class="config-section-body" v-show="!collapsedSections.pages">
              <div class="page-types-grid">
                <div
                  v-for="(pt, key) in config.page_types"
                  :key="key"
                  class="page-type-card"
                  :class="{ active: activePageType === key }"
                  @click="activePageType = key"
                >
                  <div class="pt-icon">{{ getPageTypeIcon(key) }}</div>
                  <div class="pt-name">{{ key }}</div>
                  <div class="pt-placeholders">{{ (pt.placeholders || []).length }} 个占位符</div>
                </div>
                <button class="add-page-type-btn" @click="addPageType">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                  </svg>
                </button>
              </div>
              <!-- Page Type Editor -->
              <div v-if="activePageType && config.page_types[activePageType]" class="page-type-editor">
                <div class="pte-header">
                  <span>编辑: {{ activePageType }}</span>
                  <button class="mini-btn danger" @click="removePageType(activePageType)" v-if="!isBuiltinPageType(activePageType)">
                    删除此类型
                  </button>
                </div>
                <div class="form-group">
                  <label>骨架 HTML (skeleton)</label>
                  <textarea
                    class="form-textarea code"
                    v-model="config.page_types[activePageType].skeleton"
                    rows="5"
                    placeholder='<div class="slide {{type}}">{{content}}</div>'
                  ></textarea>
                </div>
                <div class="form-group">
                  <label>占位符 (逗号分隔)</label>
                  <input
                    class="form-input"
                    :value="getPlaceholdersString(activePageType)"
                    @change="updatePlaceholders($event.target.value)"
                    placeholder="title, content"
                  >
                </div>
              </div>
            </div>
          </div>

          <!-- Raw HTML -->
          <div class="config-section">
            <div class="config-section-header" @click="toggleSection('html')">
              <span>完整 HTML</span>
              <svg :class="{ rotated: !collapsedSections.html }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
              </svg>
            </div>
            <div class="config-section-body" v-show="!collapsedSections.html">
              <textarea
                class="form-textarea code large"
                v-model="config.raw_html"
                rows="12"
                placeholder="粘贴或让 AI 生成完整的 HTML 模板..."
              ></textarea>
              <button class="btn btn-secondary btn-sm" @click="regenerateFromRaw" style="margin-top: 8px;">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                从 HTML 提取配置
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Add Color Modal -->
    <div v-if="showAddColor" class="modal-overlay active" @click.self="showAddColor = false">
      <div class="modal modal-sm">
        <div class="modal-header">
          <h3>添加颜色变量</h3>
          <button class="modal-close" @click="showAddColor = false">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>变量名</label>
            <input class="form-input" v-model="newColor.key" placeholder="color-primary">
          </div>
          <div class="form-group">
            <label>颜色值</label>
            <div class="color-picker-row">
              <input type="color" v-model="newColor.value" class="color-input">
              <input class="form-input" v-model="newColor.value" placeholder="#6366f1">
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showAddColor = false">取消</button>
          <button class="btn btn-primary" @click="addColorVar">添加</button>
        </div>
      </div>
    </div>

    <!-- Save Modal -->
    <div v-if="showSaveModal" class="modal-overlay active" @click.self="showSaveModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>保存模板</h3>
          <button class="modal-close" @click="showSaveModal = false">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>模板名称</label>
            <input class="form-input" v-model="saveConfig.name" placeholder="我的模板">
          </div>
          <div class="form-group">
            <label>描述</label>
            <input class="form-input" v-model="saveConfig.description" placeholder="模板描述...">
          </div>
          <div class="form-group">
            <label>标签 (逗号分隔)</label>
            <input class="form-input" v-model="saveConfig.tags" placeholder="自定义, 商务">
          </div>
          <div class="save-preview">
            <div class="sp-label">预览</div>
            <div class="sp-card" :style="{ background: getPreviewGradient() }">
              <div class="sp-name" :style="{ color: getPreviewTextColor() }">{{ saveConfig.name || '模板名称' }}</div>
              <div class="sp-desc" :style="{ color: getPreviewTextColor(), opacity: 0.7 }">{{ saveConfig.description || '模板描述' }}</div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showSaveModal = false">取消</button>
          <button class="btn btn-primary" @click="confirmSave" :disabled="!saveConfig.name.trim()">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { store } from '../stores/appStore'

// --- State ---
const chatContainer = ref(null)
const inputRef = ref(null)
const previewFrame = ref(null)

const messages = ref([])
const userInput = ref('')
const isTyping = ref(false)
const autoScroll = ref(true)
const showJson = ref(false)
const showAddColor = ref(false)
const showSaveModal = ref(false)
const previewScale = ref('fit')
const activeSlide = ref(0)
const activePageType = ref(null)

const jsonEditorContent = ref('')
const currentModel = ref('')

const newColor = ref({ key: '', value: '#6366f1' })

const saveConfig = ref({ name: '', description: '', tags: '' })

const collapsedSections = ref({
  basic: false,
  colors: false,
  pages: false,
  html: false
})

// Default template config
const config = ref({
  template_id: 'my_template_' + Date.now().toString(36),
  template_name: '我的自定义模板',
  description: '使用 AI 模板创建器生成的模板',
  version: '1.0.0',
  css_variables: {
    'color-primary': '#6366f1',
    'color-secondary': '#8b5cf6',
    'color-background': '#ffffff',
    'color-surface': '#f8fafc',
    'color-text': '#1e293b',
    'color-text-muted': '#64748b',
    'color-card': '#ffffff',
    'font-body': "'Segoe UI', 'Microsoft YaHei', sans-serif",
    'font-heading': "'Segoe UI', 'Microsoft YaHei', sans-serif"
  },
  page_types: {
    cover: {
      skeleton: '<div class="slide cover"><h1 class="main-title">{{title}}</h1><p class="subtitle">{{subtitle}}</p></div>',
      placeholders: ['title', 'subtitle']
    },
    content: {
      skeleton: '<div class="slide content"><h2 class="page-title">{{title}}</h2><div class="page-content">{{content}}</div></div>',
      placeholders: ['title', 'content']
    },
    toc: {
      skeleton: '<div class="slide toc"><h2 class="page-title">{{title}}</h2><div class="toc-list">{{toc_items}}</div></div>',
      placeholders: ['title', 'toc_items']
    },
    ending: {
      skeleton: '<div class="slide ending"><h1>{{title}}</h1><p>{{message}}</p></div>',
      placeholders: ['title', 'message']
    }
  },
  raw_html: '',
  viewport: { width: 1280, height: 720 },
  tags: [],
  template_type: 'user'
})

// Auto-select first page type when config loads
watch(() => Object.keys(config.value.page_types || {}), (keys) => {
  if (keys.length > 0 && !activePageType.value) {
    activePageType.value = keys[0]
  }
}, { immediate: true })

// --- Color Presets ---
const colorPresets = [
  {
    name: '赛博朋克',
    colors: ['#00ffff', '#0088ff', '#a855f7', '#ec4899'],
    vars: {
      'color-primary': '#00ffff', 'color-secondary': '#0088ff',
      'color-accent-cyan': '#00ffff', 'color-accent-blue': '#0088ff',
      'color-accent-purple': '#a855f7', 'color-accent-pink': '#ec4899',
      'color-background': '#0a0c14', 'color-surface': '#1a2035',
      'color-text': '#e0e0e0', 'color-card': '#151a2d'
    }
  },
  {
    name: '水墨风',
    colors: ['#1a1a1a', '#8B7355', '#C54B4B', '#F5F0E8'],
    vars: {
      'color-primary': '#1a1a1a', 'color-secondary': '#8B7355',
      'color-accent-seal': '#C54B4B', 'color-background': '#F5F0E8',
      'color-surface': '#FDFBF7', 'color-text': '#2d2d2d',
      'color-card': '#FFFFFF'
    }
  },
  {
    name: '商务蓝',
    colors: ['#1e3a5f', '#2c5282', '#3182ce', '#63b3ed'],
    vars: {
      'color-primary': '#1e3a5f', 'color-secondary': '#2c5282',
      'color-accent-blue': '#3182ce', 'color-accent-light': '#63b3ed',
      'color-background': '#f7fafc', 'color-surface': '#ffffff',
      'color-text': '#1a202c', 'color-card': '#ffffff'
    }
  },
  {
    name: '清新绿',
    colors: ['#166534', '#15803d', '#22c55e', '#86efac'],
    vars: {
      'color-primary': '#166534', 'color-secondary': '#15803d',
      'color-accent-green': '#22c55e', 'color-accent-light': '#86efac',
      'color-background': '#f0fdf4', 'color-surface': '#ffffff',
      'color-text': '#14532d', 'color-card': '#ffffff'
    }
  },
  {
    name: '暖橙',
    colors: ['#9a3412', '#c2410c', '#ea580c', '#fdba74'],
    vars: {
      'color-primary': '#9a3412', 'color-secondary': '#c2410c',
      'color-accent-orange': '#ea580c', 'color-accent-light': '#fdba74',
      'color-background': '#fff7ed', 'color-surface': '#ffffff',
      'color-text': '#431407', 'color-card': '#ffffff'
    }
  }
]

// --- Computed ---
const tagsString = computed({
  get: () => (config.value.tags || []).join(', '),
  set: (v) => { config.value.tags = v.split(',').map(t => t.trim()).filter(Boolean) }
})

const previewSlides = computed(() => {
  const pt = config.value.page_types || {}
  const css = config.value.css_variables || {}
  const primary = css['color-primary'] || '#6366f1'
  const bg = css['color-background'] || '#ffffff'
  const slides = []

  if (pt.cover) {
    slides.push({
      type: 'cover',
      title: config.value.template_name || '演示文稿',
      subtitle: config.value.description || 'AI 生成的演示文稿',
      skeleton: pt.cover.skeleton,
      pageNum: slides.length + 1
    })
  }

  if (pt.content) {
    slides.push({
      type: 'content',
      title: '内容页标题',
      content: '这是内容区域，可以放置文字、图片、图表等内容。这里展示的是模板骨架的实际渲染效果。',
      skeleton: pt.content.skeleton,
      pageNum: slides.length + 1
    })
  }

  if (pt.toc) {
    slides.push({
      type: 'toc',
      title: '目录',
      items: ['章节一', '章节二', '章节三'],
      skeleton: pt.toc.skeleton,
      pageNum: slides.length + 1
    })
  }

  if (pt.section) {
    slides.push({
      type: 'section',
      title: '章节标题',
      subtitle: '副标题',
      skeleton: pt.section.skeleton,
      pageNum: slides.length + 1
    })
  }

  if (pt.ending) {
    slides.push({
      type: 'ending',
      title: '谢谢观看',
      message: '感谢您的观看',
      skeleton: pt.ending.skeleton,
      pageNum: slides.length + 1
    })
  }

  return slides.length > 0 ? slides : [
    { type: 'cover', title: config.value.template_name || '演示文稿', subtitle: 'AI 生成的演示文稿', pageNum: 1 },
    { type: 'content', title: '内容页', content: '内容区域', pageNum: 2 },
    { type: 'ending', title: '谢谢观看', message: '', pageNum: 3 }
  ]
})

const previewHtml = computed(() => {
  return buildPreviewHtml()
})

const hasValidTemplate = computed(() => {
  return config.value.template_id && config.value.template_name &&
    (config.value.raw_html || config.value.page_types)
})

// --- Methods ---

function goBack() {
  store.goToTemplate()
}

function getPageTypeIcon(key) {
  const icons = { cover: '📄', content: '📝', toc: '📋', section: '🏷️', ending: '🏁', compare: '⚖️', chart: '📊', timeline: '📅', qa: '❓' }
  return icons[key] || '📄'
}

function isBuiltinPageType(key) {
  return ['cover', 'content', 'toc', 'section', 'ending', 'compare', 'chart', 'timeline', 'qa'].includes(key)
}

function toggleSection(key) {
  collapsedSections.value[key] = !collapsedSections.value[key]
}

function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
}

function toggleJsonView() {
  showJson.value = !showJson.value
  if (showJson.value) {
    jsonEditorContent.value = JSON.stringify(config.value, null, 2)
  }
}

function applyJsonEdit() {
  try {
    const parsed = JSON.parse(jsonEditorContent.value)
    config.value = parsed
    showJson.value = false
    store.showToastMessage('JSON 配置已应用')
  } catch (e) {
    store.showToastMessage('JSON 格式错误: ' + e.message)
  }
}

function updateCssVar(key, value) {
  config.value.css_variables[key] = value
}

function removeCssVar(key) {
  delete config.value.css_variables[key]
  config.value.css_variables = { ...config.value.css_variables }
}

function addColorVar() {
  if (newColor.value.key) {
    config.value.css_variables[newColor.value.key] = newColor.value.value
    newColor.value = { key: '', value: '#6366f1' }
    showAddColor.value = false
  }
}

function resolveColor(val) {
  if (!val) return '#cccccc'
  if (val.startsWith('#') || val.startsWith('rgb')) return val
  return val
}

function applyPalette(preset) {
  Object.assign(config.value.css_variables, preset.vars)
  store.showToastMessage(`已应用「${preset.name}」配色方案`)
}

function addPageType() {
  const name = prompt('输入页面类型名称 (如: about, team):')
  if (name && !config.value.page_types[name]) {
    config.value.page_types[name] = {
      skeleton: `<div class="slide ${name}"><h2>{{title}}</h2><div>{{content}}</div></div>`,
      placeholders: ['title', 'content']
    }
    activePageType.value = name
  }
}

function getPlaceholdersString(pageType) {
  const pt = config.value.page_types?.[pageType]
  if (!pt) return ''
  const pls = pt.placeholders || []
  return Array.isArray(pls) ? pls.join(', ') : String(pls)
}

function removePageType(key) {
  if (confirm(`确定删除页面类型「${key}」？`)) {
    delete config.value.page_types[key]
    const keys = Object.keys(config.value.page_types)
    activePageType.value = keys.length > 0 ? keys[0] : null
  }
}

function updatePlaceholders(val) {
  config.value.page_types[activePageType.value].placeholders = val.split(',').map(s => s.trim()).filter(Boolean)
}

function syncTags() {
  // tagsString computed handles it
}

function selectSlide(idx) {
  activeSlide.value = idx
  // Send message to iframe preview to navigate
  if (previewFrame.value && previewFrame.value.contentWindow) {
    previewFrame.value.contentWindow.postMessage({ type: 'preview-nav', slide: idx }, '*')
  }
}

function getSlideThumbStyle(slide) {
  const css = config.value.css_variables || {}
  const primary = css['color-primary'] || '#6366f1'
  const secondary = css['color-secondary'] || '#8b5cf6'
  const bg = css['color-background'] || css['color-surface'] || '#ffffff'
  const surface = css['color-surface'] || '#f8fafc'
  const isDark = isColorDark(bg)

  if (slide.type === 'cover' || slide.type === 'ending') {
    if (isDark) {
      return `linear-gradient(135deg, ${bg}, ${adjustBrightness(bg, 20)})`
    }
    return `linear-gradient(135deg, ${primary}, ${secondary})`
  }
  if (slide.type === 'section') {
    return `linear-gradient(135deg, ${primary}, ${secondary})`
  }
  if (slide.type === 'toc') {
    return `linear-gradient(135deg, ${bg}, ${surface})`
  }
  return bg
}

function onPreviewLoad() {
  // Preview loaded
}

function openFullscreen() {
  const win = window.open('', '_blank')
  win.document.write(previewHtml.value)
  win.document.close()
}

function resetAll() {
  if (confirm('确定要重置所有对话和配置吗？')) {
    messages.value = []
    config.value = {
      template_id: 'my_template_' + Date.now().toString(36),
      template_name: '我的自定义模板',
      description: '使用 AI 模板创建器生成的模板',
      version: '1.0.0',
      css_variables: {
        'color-primary': '#6366f1', 'color-secondary': '#8b5cf6',
        'color-background': '#ffffff', 'color-surface': '#f8fafc',
        'color-text': '#1e293b', 'color-text-muted': '#64748b',
        'color-card': '#ffffff',
        'font-body': "'Segoe UI', 'Microsoft YaHei', sans-serif",
        'font-heading': "'Segoe UI', 'Microsoft YaHei', sans-serif"
      },
      page_types: {
        cover: { skeleton: '<div class="slide cover"><h1 class="main-title">{{title}}</h1><p class="subtitle">{{subtitle}}</p></div>', placeholders: ['title', 'subtitle'] },
        content: { skeleton: '<div class="slide content"><h2 class="page-title">{{title}}</h2><div class="page-content">{{content}}</div></div>', placeholders: ['title', 'content'] },
        toc: { skeleton: '<div class="slide toc"><h2 class="page-title">{{title}}</h2><div class="toc-list">{{toc_items}}</div></div>', placeholders: ['title', 'toc_items'] },
        ending: { skeleton: '<div class="slide ending"><h1>{{title}}</h1><p>{{message}}</p></div>', placeholders: ['title', 'message'] }
      },
      raw_html: '',
      viewport: { width: 1280, height: 720 },
      tags: [],
      template_type: 'user'
    }
    store.showToastMessage('已重置')
  }
}

function saveTemplate() {
  saveConfig.value = {
    name: config.value.template_name,
    description: config.value.description,
    tags: (config.value.tags || []).join(', ')
  }
  showSaveModal.value = true
}

function confirmSave() {
  const templateData = {
    template_id: config.value.template_id || 'custom_' + Date.now().toString(36).slice(-6),
    template_name: saveConfig.value.name || config.value.template_name,
    description: saveConfig.value.description || config.value.description,
    version: config.value.version || '1.0.0',
    css_variables: config.value.css_variables || {},
    page_types: config.value.page_types || {},
    tags: saveConfig.value.tags
      ? saveConfig.value.tags.split(',').map(t => t.trim()).filter(Boolean)
      : config.value.tags || [],
    viewport: config.value.viewport || { width: 1280, height: 720 },
    template_type: 'user'
  }

  store.createTemplate(templateData).then(() => {
    showSaveModal.value = false
    store.showToastMessage('模板已保存')
  }).catch(err => {
    store.showToastMessage('保存失败: ' + err.message)
  })
}

function getPreviewGradient() {
  const css = config.value.css_variables || {}
  const primary = css['color-primary'] || '#6366f1'
  const secondary = css['color-secondary'] || '#8b5cf6'
  const bg = css['color-background'] || css['color-surface'] || '#ffffff'
  return isColorDark(bg)
    ? `linear-gradient(135deg, ${bg}, ${adjustBrightness(bg, 20)})`
    : `linear-gradient(135deg, ${primary}, ${secondary})`
}

function getPreviewTextColor() {
  const css = config.value.css_variables || {}
  const bg = css['color-background'] || css['color-surface'] || '#ffffff'
  return isColorDark(bg) ? '#ffffff' : (css['color-text'] || '#1a1a1a')
}

// --- LLM Integration ---

const SYSTEM_PROMPT = `你是一个专业的 PPT 模板设计师。用户会描述他们想要的模板风格，你需要生成完整的模板 JSON 配置。

请按照以下格式回复（可以是纯 JSON 或带解释的 Markdown，然后是 JSON 代码块）：

{
  "template_id": "模板唯一ID（小写字母+下划线）",
  "template_name": "模板名称",
  "description": "模板描述",
  "css_variables": {
    "color-primary": "#主色调",
    "color-secondary": "#次色调",
    "color-background": "#背景色",
    "color-surface": "#卡片/表面色",
    "color-text": "#主文字色",
    "color-text-muted": "#次要文字色",
    "color-card": "#卡片背景色",
    "font-body": "正文字体",
    "font-heading": "标题字体",
    "color-accent-*": "#点缀色"
  },
  "page_types": {
    "cover": { "skeleton": "HTML骨架", "placeholders": ["占位符列表"] },
    "content": { "skeleton": "HTML骨架", "placeholders": ["占位符列表"] },
    "toc": { "skeleton": "HTML骨架", "placeholders": ["占位符列表"] },
    "section": { "skeleton": "HTML骨架", "placeholders": ["占位符列表"] },
    "ending": { "skeleton": "HTML骨架", "placeholders": ["占位符列表"] }
  },
  "tags": ["标签1", "标签2"],
  "viewport": { "width": 1280, "height": 720 }
}

注意：
1. 只回复 JSON，不要回复其他内容
2. 颜色使用有效的十六进制颜色码
3. HTML 骨架要简洁、可复用
4. 字体使用系统自带或 Google Fonts
5. 尽量包含所有常见页面类型
`

async function sendMessage() {
  const text = userInput.value.trim()
  if (!text || isTyping.value) return

  const userMsg = {
    role: 'user',
    content: text,
    time: formatTime(new Date())
  }
  messages.value.push(userMsg)
  userInput.value = ''
  isTyping.value = true

  await scrollToBottom()
  await nextTick()

  try {
    const history = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content
    }))

    const response = await callLLM(text, history)

    const assistantMsg = {
      role: 'assistant',
      content: extractTextFromResponse(response),
      llmResponse: response,
      parsedConfig: response.parsed,
      showFull: false,
      time: formatTime(new Date())
    }
    messages.value.push(assistantMsg)

    // Apply parsed config from LLM response
    if (response.parsed) {
      mergeConfig(response.parsed)
      store.showToastMessage('模板配置已更新')
    }
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，发生了错误: ' + err.message + '\n\n你可以手动编辑右侧的配置面板。',
      llmResponse: null,
      parsedConfig: null,
      showFull: false,
      time: formatTime(new Date())
    })
  }

  isTyping.value = false
  await nextTick()
  await scrollToBottom()
}

async function callLLM(message, history = []) {
  try {
    const res = await fetch('/api/llm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          ...history,
          { role: 'user', content: message }
        ],
        mode: 'template'
      })
    })
    if (res.ok) {
      const data = await res.json()
      currentModel.value = data.model || 'deepseek-chat'
      return data
    }
    console.warn(`LLM API 返回错误状态 ${res.status}，使用本地生成`)
  } catch (e) {
    console.warn('LLM API 调用失败，将使用本地生成:', e)
  }

  // Fallback: generate locally based on keywords
  return generateLocalFallback(message)
}

function generateLocalFallback(message) {
  const lower = message.toLowerCase()
  let result

  if (lower.includes('商务') || lower.includes('business')) {
    result = { template_id: 'business_pro', template_name: '商务专业', description: '简洁大气的商务风格模板', css_variables: { 'color-primary': '#1e3a5f', 'color-secondary': '#2c5282', 'color-accent-gold': '#d4af37', 'color-background': '#f8fafc', 'color-surface': '#ffffff', 'color-text': '#1a202c', 'color-text-muted': '#64748b', 'color-card': '#ffffff', 'font-body': "'Segoe UI', 'Microsoft YaHei', sans-serif", 'font-heading': "'Segoe UI', 'Microsoft YaHei', sans-serif" }, page_types: { cover: { skeleton: '<div class="slide cover"><div class="cover-bg"></div><div class="cover-content"><h1 class="main-title">{{title}}</h1><p class="subtitle">{{subtitle}}</p><div class="cover-meta"><span class="date-badge">{{date_badge}}</span></div></div></div>', placeholders: ['title', 'subtitle', 'date_badge'] }, content: { skeleton: '<div class="slide content"><div class="content-header"><h2 class="page-title">{{title}}</h2></div><div class="content-body">{{content}}</div><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'content', 'page_number'] }, toc: { skeleton: '<div class="slide toc"><h2 class="page-title">{{title}}</h2><div class="toc-list">{{toc_items}}</div><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'toc_items', 'page_number'] }, section: { skeleton: '<div class="slide section"><h1 class="section-title">{{title}}</h1><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'page_number'] }, ending: { skeleton: '<div class="slide ending"><h1 class="ending-title">{{title}}</h1><p class="ending-message">{{message}}</p><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'message', 'page_number'] } }, tags: ['商务', '专业', '简洁'], viewport: { width: 1280, height: 720 } }
  } else if (lower.includes('科技') || lower.includes('tech') || lower.includes('赛博') || lower.includes('cyber')) {
    result = { template_id: 'cyber_tech', template_name: '赛博科技', description: '未来科技感的赛博朋克风格模板', css_variables: { 'color-primary': '#00ffff', 'color-secondary': '#0088ff', 'color-accent-cyan': '#00ffff', 'color-accent-blue': '#0088ff', 'color-accent-purple': '#a855f7', 'color-background': '#0a0c14', 'color-surface': '#1a2035', 'color-text': '#e0e0e0', 'color-text-muted': '#a0a0a0', 'color-card': '#151a2d', 'font-body': "'Segoe UI', 'Microsoft YaHei', sans-serif", 'font-heading': "'Segoe UI', 'Microsoft YaHei', sans-serif" }, page_types: { cover: { skeleton: '<div class="slide cover"><div class="grid-bg"></div><div class="particles"></div><div class="title-box"><h1 class="main-title">{{title}}</h1><p class="subtitle">{{subtitle}}</p></div></div>', placeholders: ['title', 'subtitle'] }, content: { skeleton: '<div class="slide content"><div class="circuit-bg"></div><div class="page-title"><i class="fa-solid fa-microchip"></i>{{title}}</div><div class="page-content">{{content}}</div><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'content', 'page_number'] }, toc: { skeleton: '<div class="slide toc"><div class="hex-grid"></div><div class="page-title">{{title}}</div><div class="toc-grid">{{toc_items}}</div><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'toc_items', 'page_number'] }, section: { skeleton: '<div class="slide section"><h1 class="section-title">{{title}}</h1><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'page_number'] }, ending: { skeleton: '<div class="slide ending"><div class="stars-bg"></div><h1 class="ending-title">{{title}}</h1><p class="ending-message">{{message}}</p><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'message', 'page_number'] } }, tags: ['科技', '赛博朋克', '深色', '未来'], viewport: { width: 1280, height: 720 } }
  } else if (lower.includes('水墨') || lower.includes('中国') || lower.includes('文艺')) {
    result = { template_id: 'ink_wash', template_name: '水墨中国风', description: '清新淡雅的水墨画风格，适合诗词文学展示', css_variables: { 'color-primary': '#1a1a1a', 'color-secondary': '#8B7355', 'color-accent-seal': '#C54B4B', 'color-background': '#F5F0E8', 'color-surface': '#FDFBF7', 'color-text': '#2d2d2d', 'color-text-muted': '#6b6b6b', 'color-card': '#FFFFFF', 'font-body': "'STSong', 'SimSun', 'Noto Serif SC', serif", 'font-heading': "'STKaiti', 'KaiTi', 'Noto Serif SC', serif" }, page_types: { cover: { skeleton: '<div class="slide cover"><div class="ink-wash-bg"></div><div class="seal-mark">印</div><div class="title-box"><h1 class="main-title">{{title}}</h1><p class="subtitle">{{subtitle}}</p></div></div>', placeholders: ['title', 'subtitle'] }, content: { skeleton: '<div class="slide content"><div class="ink-wash-bg"></div><div class="ink-border-top"></div><div class="ink-border-bottom"></div><div class="seal-mark-small">印</div><div class="page-title-wrap"><h2 class="page-title">{{title}}</h2></div><div class="page-content">{{content}}</div><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'content', 'page_number'] }, toc: { skeleton: '<div class="slide toc"><div class="ink-wash-bg"></div><div class="page-title-wrap"><h2 class="page-title">{{title}}</h2></div><div class="toc-list">{{toc_items}}</div><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'toc_items', 'page_number'] }, section: { skeleton: '<div class="slide section"><div class="ink-wash-bg"></div><div class="seal-mark">印</div><h1 class="section-title">{{title}}</h1><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'page_number'] }, ending: { skeleton: '<div class="slide ending"><div class="ink-wash-bg"></div><div class="seal-mark">印</div><h1 class="ending-title">{{title}}</h1><p class="ending-message">{{message}}</p><div class="seal-stamp">谢谢观赏</div><div class="slide-footer"><span class="page-num">{{page_number}}</span></div></div>', placeholders: ['title', 'message', 'page_number'] } }, tags: ['水墨', '中国风', '传统', '典雅'], viewport: { width: 1280, height: 720 } }
  } else {
    result = { template_id: 'custom_' + Date.now().toString(36).slice(-6), template_name: '自定义模板', description: '根据你的需求生成的模板', css_variables: { 'color-primary': '#6366f1', 'color-secondary': '#8b5cf6', 'color-background': '#ffffff', 'color-surface': '#f8fafc', 'color-text': '#1e293b', 'color-text-muted': '#64748b', 'color-card': '#ffffff', 'font-body': "'Segoe UI', 'Microsoft YaHei', sans-serif", 'font-heading': "'Segoe UI', 'Microsoft YaHei', sans-serif" }, page_types: { cover: { skeleton: '<div class="slide cover"><h1 class="main-title">{{title}}</h1><p class="subtitle">{{subtitle}}</p></div>', placeholders: ['title', 'subtitle'] }, content: { skeleton: '<div class="slide content"><h2 class="page-title">{{title}}</h2><div class="page-content">{{content}}</div></div>', placeholders: ['title', 'content'] }, toc: { skeleton: '<div class="slide toc"><h2 class="page-title">{{title}}</h2><div class="toc-list">{{toc_items}}</div></div>', placeholders: ['title', 'toc_items'] }, ending: { skeleton: '<div class="slide ending"><h1 class="ending-title">{{title}}</h1><p class="ending-message">{{message}}</p></div>', placeholders: ['title', 'message'] } }, tags: ['自定义'], viewport: { width: 1280, height: 720 } }
  }

  return { success: true, response: JSON.stringify(result, null, 2), parsed: result, model: 'local-fallback' }
}

function mergeConfig(parsed) {
  if (parsed.template_id) config.value.template_id = parsed.template_id
  if (parsed.template_name) config.value.template_name = parsed.template_name
  if (parsed.description) config.value.description = parsed.description
  if (parsed.version) config.value.version = parsed.version
  if (parsed.css_variables) {
    config.value.css_variables = { ...config.value.css_variables, ...parsed.css_variables }
  }
  if (parsed.page_types) {
    for (const [key, val] of Object.entries(parsed.page_types)) {
      config.value.page_types[key] = {
        skeleton: val.skeleton || val.html || `<div class="slide ${key}"><h2>{{title}}</h2><div>{{content}}</div></div>`,
        placeholders: val.placeholders || val.fields || ['title']
      }
    }
  }
  if (parsed.tags) config.value.tags = parsed.tags
  if (parsed.viewport) config.value.viewport = parsed.viewport
}

function extractTextFromResponse(response) {
  if (typeof response === 'string') {
    return response.replace(/```json\n?([\s\S]*?)\n?```/g, '[JSON配置]').trim()
  }
  return response.parsed
    ? `已生成模板「${response.parsed.template_name || '自定义模板'}」，包含 ${Object.keys(response.parsed.page_types || {}).length} 种页面类型。`
    : '已收到响应'
}

function extractHtmlFromResponse(response) {
  if (typeof response === 'string') {
    const match = response.match(/```html\n?([\s\S]*?)\n?```/)
    return match ? match[1] : null
  }
  return response.html_content || null
}

function extractJsonFromResponse(response) {
  if (typeof response === 'string') {
    const match = response.match(/```json\n?([\s\S]*?)\n?```/) || response.match(/\{[\s\S]*\}/)
    if (match) {
      return match[0].replace(/```json\n?/, '').replace(/```$/, '').trim()
    }
    return '{}'
  }
  if (response.parsed) {
    return JSON.stringify(response.parsed, null, 2)
  }
  return '{}'
}

function formatJson(obj) {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

function applyHtmlPreview(msg) {
  if (msg.htmlContent) {
    config.value.raw_html = msg.htmlContent
    store.showToastMessage('HTML 设计已应用')
  }
}

function sendQuickPrompt(prompt) {
  userInput.value = prompt
  sendMessage()
}

// --- Build Preview HTML ---
function buildPreviewHtml() {
  const css = config.value.css_variables || {}
  const primary = css['color-primary'] || '#6366f1'
  const secondary = css['color-secondary'] || '#8b5cf6'
  const bg = css['color-background'] || '#ffffff'
  const surface = css['color-surface'] || '#f8fafc'
  const text = css['color-text'] || '#1e293b'
  const textMuted = css['color-text-muted'] || '#64748b'
  const card = css['color-card'] || '#ffffff'
  const accent1 = css['color-accent-1'] || css['color-accent-cyan'] || css['color-accent-blue'] || secondary
  const accent2 = css['color-accent-2'] || css['color-accent-purple'] || accent1
  const fontBody = css['font-body'] || "'Segoe UI', 'Microsoft YaHei', sans-serif"
  const fontHeading = css['font-heading'] || "'Segoe UI', 'Microsoft YaHei', sans-serif"
  const isDark = isColorDark(bg)

  // Determine text colors based on background
  const onPrimary = '#ffffff'
  const onBg = isDark ? '#f0f0f0' : text
  const onBgMuted = isDark ? '#a0a0a0' : textMuted

  const slides = previewSlides.value

  // Build per-slide HTML using skeleton or fallback
  const slidesHtml = slides.map((s, i) => {
    let body = ''

    if (s.skeleton) {
      // Replace placeholders in skeleton
      body = s.skeleton
        .replace(/\{\{title\}\}/g, escapeHtml(s.title || ''))
        .replace(/\{\{subtitle\}\}/g, escapeHtml(s.subtitle || s.content || ''))
        .replace(/\{\{content\}\}/g, escapeHtml(s.content || ''))
        .replace(/\{\{message\}\}/g, escapeHtml(s.message || ''))
        .replace(/\{\{toc_items\}\}/g, buildTocItems(s.items || [], primary, text, surface, isDark))
        .replace(/\{\{date_badge\}\}/g, escapeHtml(new Date().toLocaleDateString('zh-CN')))
        .replace(/\{\{page_number\}\}/g, String(s.pageNum))
    } else {
      // Fallback rendering based on slide type
      if (s.type === 'cover') {
        body = buildCoverSlide(s, primary, secondary, bg, onPrimary, fontHeading, isDark)
      } else if (s.type === 'content') {
        body = buildContentSlide(s, primary, bg, surface, text, textMuted, card, fontBody, fontHeading, onBg, onBgMuted)
      } else if (s.type === 'toc') {
        body = buildTocSlide(s, primary, bg, surface, text, fontBody, fontHeading, onBg, onBgMuted, isDark)
      } else if (s.type === 'section') {
        body = buildSectionSlide(s, primary, secondary, bg, onPrimary, fontHeading, isDark)
      } else if (s.type === 'ending') {
        body = buildEndingSlide(s, primary, secondary, bg, onPrimary, fontHeading, isDark)
      }
    }

    return `<div class="slide ${s.type}" data-slide="${i}" style="
      width: 1280px;
      height: 720px;
      flex-shrink: 0;
      position: relative;
      overflow: hidden;
      background: ${bg};
      font-family: ${fontBody};
    ">
      ${body}
      <div style="position: absolute; bottom: 12px; left: 0; right: 0; text-align: center; color: ${onBgMuted}; font-size: 12px; opacity: 0.4;">
        ${i + 1} / ${slides.length}
      </div>
    </div>`
  }).join('')

  // Navigation dots HTML
  const dotsHtml = slides.map((s, i) =>
    `<div class="dot${i === activeSlide.value ? ' active' : ''}" data-i="${i}" style="
      width: 8px; height: 8px; border-radius: 50%;
      background: ${i === activeSlide.value ? primary : 'rgba(255,255,255,0.3)'};
      cursor: pointer; transition: all 0.2s;
    "></div>`
  ).join('')

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    width: 100%; height: 100%;
    background: #111;
    overflow: hidden;
    font-family: ${fontBody};
  }
  .slides-wrapper {
    display: flex;
    width: 100%; height: 100%;
    align-items: center;
    justify-content: center;
  }
  .slides-track {
    display: flex;
    transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    transform: translateX(-${activeSlide.value * 1280}px);
  }
  .dot-bar {
    position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
    display: flex; gap: 8px; z-index: 100;
  }
  .slide { display: flex; flex-direction: column; }
  h1, h2, p { margin: 0; padding: 0; }
  /* Common slide elements */
  .slide-cover { align-items: center; justify-content: center; }
  .slide-cover .cover-title {
    font-size: 72px; font-weight: 800;
    color: ${onPrimary};
    text-align: center;
    text-shadow: 0 4px 20px rgba(0,0,0,0.3);
    line-height: 1.1;
    margin-bottom: 16px;
  }
  .slide-cover .cover-subtitle {
    font-size: 24px; color: ${onPrimary}; opacity: 0.85;
    text-align: center;
  }
  .slide-cover .cover-gradient {
    position: absolute; inset: 0; z-index: 0;
    background: linear-gradient(135deg, ${primary} 0%, ${secondary} 100%);
  }
  .slide-cover .cover-content { position: relative; z-index: 1; text-align: center; }

  .slide-content { padding: 48px 64px; }
  .slide-content .content-header {
    border-bottom: 3px solid ${primary};
    padding-bottom: 12px; margin-bottom: 24px;
  }
  .slide-content .content-title {
    font-size: 36px; font-weight: 700;
    color: ${primary};
    font-family: ${fontHeading};
  }
  .slide-content .content-body {
    font-size: 18px; color: ${text};
    line-height: 1.8; flex: 1;
  }
  .slide-content .content-body ul {
    padding-left: 24px; margin-top: 8px;
  }
  .slide-content .content-body li {
    margin-bottom: 8px; color: ${text};
  }
  .slide-content .content-card {
    background: ${card};
    border: 1px solid ${primary}20;
    border-radius: 12px; padding: 20px 24px;
    margin-top: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  }
  .slide-content .content-card-title {
    font-size: 16px; font-weight: 600; color: ${primary}; margin-bottom: 8px;
  }

  .slide-toc { padding: 48px 64px; }
  .slide-toc .toc-title {
    font-size: 36px; font-weight: 700; color: ${primary};
    font-family: ${fontHeading}; margin-bottom: 32px;
  }
  .slide-toc .toc-item {
    background: ${surface};
    border: 1px solid ${primary}25;
    border-radius: 10px; padding: 16px 24px;
    margin-bottom: 12px;
    display: flex; align-items: center; gap: 16px;
    transition: all 0.2s;
  }
  .slide-toc .toc-num {
    width: 40px; height: 40px; border-radius: 50%;
    background: ${primary}15; color: ${primary};
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 16px; flex-shrink: 0;
  }
  .slide-toc .toc-text {
    font-size: 20px; color: ${text}; font-weight: 500;
  }

  .slide-section {
    align-items: center; justify-content: center;
  }
  .slide-section .section-gradient {
    position: absolute; inset: 0; z-index: 0;
    background: linear-gradient(135deg, ${primary} 0%, ${secondary} 100%);
  }
  .slide-section .section-content { position: relative; z-index: 1; text-align: center; }
  .slide-section .section-title {
    font-size: 64px; font-weight: 800;
    color: ${onPrimary}; text-align: center;
  }
  .slide-section .section-subtitle {
    font-size: 20px; color: ${onPrimary}; opacity: 0.75;
    margin-top: 12px; text-align: center;
  }

  .slide-ending {
    align-items: center; justify-content: center;
  }
  .slide-ending .ending-gradient {
    position: absolute; inset: 0; z-index: 0;
    background: linear-gradient(135deg, ${secondary} 0%, ${primary} 100%);
  }
  .slide-ending .ending-content { position: relative; z-index: 1; text-align: center; }
  .slide-ending .ending-title {
    font-size: 60px; font-weight: 800;
    color: ${onPrimary}; text-align: center; margin-bottom: 12px;
  }
  .slide-ending .ending-message {
    font-size: 22px; color: ${onPrimary}; opacity: 0.8;
  }
</style>
</head>
<body>
<div class="slides-wrapper">
  <div class="slides-track" id="t">
    ${slidesHtml}
  </div>
</div>
<div class="dot-bar">${dotsHtml}</div>
<script>
(function() {
  let cur = ${activeSlide.value};
  const t = document.getElementById('t');
  const dots = document.querySelectorAll('.dot');
  const total = ${slides.length};
  const W = 1280;

  function go(idx) {
    cur = Math.max(0, Math.min(idx, total - 1));
    t.style.transform = 'translateX(-' + (cur * W) + 'px)';
    dots.forEach((d, i) => {
      d.style.background = i === cur ? '${primary}' : 'rgba(255,255,255,0.3)';
    });
  }

  dots.forEach((d, i) => {
    d.addEventListener('click', () => go(i));
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') { go(cur + 1); }
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { go(cur - 1); }
  });

  document.addEventListener('wheel', e => {
    if (e.deltaY > 0) go(cur + 1);
    else go(cur - 1);
  }, { passive: true });

  window.addEventListener('message', e => {
    if (e.data && e.data.type === 'preview-nav') go(e.data.slide || 0);
  });
})();
<\/script>
</body>
</html>`
}

function buildCoverSlide(s, primary, secondary, bg, onPrimary, fontHeading, isDark) {
  const gradient = `<div style="position:absolute;inset:0;background:linear-gradient(135deg,${primary} 0%,${secondary} 100%);"></div>`
  return gradient + `<div style="position:relative;z-index:1;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;padding:40px;">
  <h1 style="font-size:72px;font-weight:800;color:${onPrimary};text-align:center;text-shadow:0 4px 20px rgba(0,0,0,0.3);line-height:1.1;margin-bottom:16px;font-family:${fontHeading};">${escapeHtml(s.title)}</h1>
  ${s.subtitle ? `<p style="font-size:24px;color:${onPrimary};opacity:0.85;text-align:center;">${escapeHtml(s.subtitle)}</p>` : ''}
</div>`
}

function buildContentSlide(s, primary, bg, surface, text, textMuted, card, fontBody, fontHeading, onBg, onBgMuted) {
  const bullets = (s.content || '').split('\n').filter(Boolean)
  const bulletsHtml = bullets.length > 0
    ? `<ul style="padding-left:24px;margin-top:8px;">${bullets.map(b => `<li style="font-size:18px;color:${text};margin-bottom:8px;line-height:1.6;">${escapeHtml(b)}</li>`).join('')}</ul>`
    : `<div style="background:${surface};border:1px solid ${primary}20;border-radius:12px;padding:24px;margin-top:16px;">
        <div style="font-size:16px;font-weight:600;color:${primary};margin-bottom:8px;">内容卡片</div>
        <div style="font-size:16px;color:${textMuted};line-height:1.6;">${escapeHtml(s.content || '这里是内容区域，可以放置文字、图片、图表等内容。')}</div>
       </div>`
  return `<div style="padding:48px 64px;display:flex;flex-direction:column;height:100%;">
  <div style="border-bottom:3px solid ${primary};padding-bottom:12px;margin-bottom:24px;">
    <h2 style="font-size:36px;font-weight:700;color:${primary};font-family:${fontHeading};">${escapeHtml(s.title)}</h2>
  </div>
  <div style="flex:1;font-size:18px;color:${text};line-height:1.8;font-family:${fontBody};">${bulletsHtml}</div>
</div>`
}

function buildTocSlide(s, primary, bg, surface, text, fontBody, fontHeading, onBg, onBgMuted, isDark) {
  const items = s.items || ['章节一', '章节二', '章节三']
  const itemsHtml = items.map((item, idx) =>
    `<div style="background:${surface};border:1px solid ${primary}25;border-radius:10px;padding:16px 24px;margin-bottom:12px;display:flex;align-items:center;gap:16px;">
      <span style="width:40px;height:40px;border-radius:50%;background:${primary}15;color:${primary};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;flex-shrink:0;">${idx + 1}</span>
      <span style="font-size:20px;color:${text};font-weight:500;">${escapeHtml(item)}</span>
    </div>`
  ).join('')
  return `<div style="padding:48px 64px;">
  <h2 style="font-size:36px;font-weight:700;color:${primary};font-family:${fontHeading};margin-bottom:32px;">${escapeHtml(s.title)}</h2>
  ${itemsHtml}
</div>`
}

function buildSectionSlide(s, primary, secondary, bg, onPrimary, fontHeading, isDark) {
  return `<div style="position:absolute;inset:0;background:linear-gradient(135deg,${primary} 0%,${secondary} 100%);display:flex;align-items:center;justify-content:center;">
  <div style="text-align:center;">
    <h1 style="font-size:64px;font-weight:800;color:${onPrimary};text-align:center;font-family:${fontHeading};">${escapeHtml(s.title)}</h1>
    ${s.subtitle ? `<p style="font-size:20px;color:${onPrimary};opacity:0.75;margin-top:12px;">${escapeHtml(s.subtitle)}</p>` : ''}
  </div>
</div>`
}

function buildEndingSlide(s, primary, secondary, bg, onPrimary, fontHeading, isDark) {
  return `<div style="position:absolute;inset:0;background:linear-gradient(135deg,${secondary} 0%,${primary} 100%);display:flex;align-items:center;justify-content:center;">
  <div style="text-align:center;">
    <h1 style="font-size:60px;font-weight:800;color:${onPrimary};text-align:center;font-family:${fontHeading};margin-bottom:12px;">${escapeHtml(s.title)}</h1>
    ${s.message ? `<p style="font-size:22px;color:${onPrimary};opacity:0.8;">${escapeHtml(s.message)}</p>` : ''}
  </div>
</div>`
}

function buildTocItems(items, primary, text, surface, isDark) {
  const textColor = isColorDark(surface) ? '#f0f0f0' : text
  return items.map((item, idx) =>
    `<div style="background:${surface};border:1px solid ${primary}25;border-radius:10px;padding:16px 24px;margin-bottom:12px;display:flex;align-items:center;gap:16px;">
      <span style="width:40px;height:40px;border-radius:50%;background:${primary}15;color:${primary};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;flex-shrink:0;">${idx + 1}</span>
      <span style="font-size:20px;color:${textColor};font-weight:500;">${escapeHtml(item)}</span>
    </div>`
  ).join('')
}

function escapeHtml(str) {
  if (!str) return ''
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function regenerateFromRaw() {
  store.showToastMessage('从 raw_html 提取配置的功能开发中')
}

// --- Utility ---
function scrollToBottom() {
  return new Promise(resolve => {
    setTimeout(() => {
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
      }
      resolve()
    }, 50)
  })
}

function formatTime(date) {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function isColorDark(color) {
  if (!color) return false
  color = color.replace('#', '')
  if (color.length === 3) color = color[0] + color[0] + color[1] + color[1] + color[2] + color[2]
  if (color.length !== 6) return false
  const r = parseInt(color.substring(0, 2), 16)
  const g = parseInt(color.substring(2, 4), 16)
  const b = parseInt(color.substring(4, 6), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 < 128
}

function adjustBrightness(hex, percent) {
  if (!hex) return '#333333'
  hex = hex.replace('#', '')
  if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2]
  if (hex.length !== 6) return '#333333'
  const num = parseInt(hex, 16)
  const amt = Math.round(2.55 * percent)
  const R = Math.min(255, Math.max(0, (num >> 16) + amt))
  const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amt))
  const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt))
  return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)
}

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

// --- Watchers ---
watch(messages, () => {
  if (autoScroll.value) {
    nextTick(() => scrollToBottom())
  }
}, { deep: true })

// --- Lifecycle ---
onMounted(() => {
  if (inputRef.value) {
    inputRef.value.focus()
  }
})
</script>

<style scoped>
/* ===================== Layout ===================== */
.creator-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.creator-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
  flex-shrink: 0;
  z-index: 10;
}

.creator-header-left, .creator-header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.creator-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.creator-title svg {
  width: 20px;
  height: 20px;
  color: var(--accent);
}

.creator-main {
  flex: 1;
  display: grid;
  grid-template-columns: 380px 1fr 360px;
  overflow: hidden;
}

/* ===================== Panel Base ===================== */
.panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border);
}

.panel:last-child {
  border-right: none;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.panel-title svg {
  width: 16px;
  height: 16px;
  color: var(--accent);
}

.panel-actions {
  display: flex;
  gap: 4px;
}

.icon-btn {
  width: 30px;
  height: 30px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.icon-btn svg {
  width: 15px;
  height: 15px;
}

.icon-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.icon-btn.active {
  background: var(--accent);
  color: white;
}

/* ===================== Chat Panel ===================== */
.panel-chat {
  background: var(--bg-primary);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scroll-behavior: smooth;
}

.chat-welcome {
  text-align: center;
  padding: 24px 16px;
  margin-bottom: 16px;
}

.welcome-orb {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
}

.welcome-orb svg {
  width: 28px;
  height: 28px;
  color: white;
}

.chat-welcome h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.chat-welcome p {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 20px;
}

.quick-prompts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.quick-prompt {
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s;
  text-align: left;
}

.quick-prompt:hover {
  background: var(--bg-tertiary);
  border-color: var(--accent);
  color: var(--text-primary);
}

.qp-icon {
  font-size: 16px;
}

/* Messages */
.message {
  display: flex;
  gap: 10px;
  animation: msgIn 0.3s ease;
}

@keyframes msgIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.avatar.user {
  background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
  color: white;
}

.avatar.ai {
  background: var(--bg-tertiary);
  color: var(--accent);
  border: 1px solid var(--border);
}

.avatar.ai svg {
  width: 16px;
  height: 16px;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.message.user .message-header {
  flex-direction: row-reverse;
}

.message-role {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
}

.message-time {
  font-size: 10px;
  color: var(--text-muted);
}

.message-body {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-primary);
}

.message.user .message-body {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.message-body code {
  background: rgba(0,0,0,0.08);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 12px;
}

.message.user .message-body code {
  background: rgba(255,255,255,0.15);
}

.message-html-preview {
  margin-top: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.html-preview-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 11px;
  color: #22c55e;
  background: rgba(34, 197, 94, 0.08);
  border-bottom: 1px solid var(--border);
}

.html-preview-label svg {
  width: 13px;
  height: 13px;
}

.html-preview-actions {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
}

.mini-btn {
  padding: 4px 12px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.mini-btn:hover {
  opacity: 0.85;
}

.mini-btn.ghost {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.mini-btn.danger {
  background: #ef4444;
  color: white;
}

.html-code {
  padding: 12px;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  overflow-x: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: monospace;
}

/* Template Preview in Chat */
.message-template-preview {
  margin-top: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.mtp-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
  background: rgba(99, 102, 241, 0.08);
  border-bottom: 1px solid var(--border);
}

.mtp-label svg {
  width: 14px;
  height: 14px;
  color: #22c55e;
}

.mtp-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  flex-wrap: wrap;
}

.mtp-tag {
  padding: 2px 8px;
  background: var(--bg-tertiary);
  color: var(--text-muted);
  border-radius: 4px;
  font-size: 11px;
}

.mtp-pages {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}

.mtp-actions {
  padding: 6px 12px 8px;
}

.mtp-code {
  padding: 12px;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  overflow-x: auto;
  max-height: 240px;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: monospace;
  border-top: 1px solid var(--border);
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: typing 1.2s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* Chat Input */
.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.input-hints {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.input-hint-label {
  font-size: 11px;
  color: var(--text-muted);
}

.input-hint {
  font-size: 11px;
  color: var(--accent);
  background: rgba(99, 102, 241, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.input-hint:hover {
  background: rgba(99, 102, 241, 0.15);
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-primary);
  resize: none;
  font-family: inherit;
  line-height: 1.5;
  max-height: 120px;
  transition: border-color 0.15s;
  outline: none;
}

.chat-input:focus {
  border-color: var(--accent);
}

.chat-input::placeholder {
  color: var(--text-muted);
}

.send-btn {
  width: 40px;
  height: 40px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
}

.send-btn:hover:not(:disabled) {
  opacity: 0.85;
  transform: scale(1.05);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.send-btn svg {
  width: 18px;
  height: 18px;
}

.input-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 10px;
  color: var(--text-muted);
}

/* ===================== Preview Panel ===================== */
.panel-preview {
  background: #111;
}

.preview-container {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.preview-container.fit .preview-frame {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.5);
}

.preview-container.\31 00 .preview-frame {
  width: 1280px;
  height: 720px;
  border: none;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.5);
}

.preview-frame {
  display: block;
}

.preview-slides {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  background: #1a1a1a;
  border-top: 1px solid #333;
  overflow-x: auto;
  flex-shrink: 0;
}

.slide-thumb {
  width: 100px;
  height: 56px;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.15s;
  flex-shrink: 0;
}

.slide-thumb.active {
  border-color: var(--accent);
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.5);
}

.slide-thumb:hover {
  transform: scale(1.05);
}

.thumb-inner {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.thumb-number {
  position: absolute;
  bottom: 2px;
  right: 4px;
  font-size: 9px;
  color: rgba(255,255,255,0.5);
  background: rgba(0,0,0,0.4);
  padding: 1px 4px;
  border-radius: 2px;
}

/* ===================== Config Panel ===================== */
.panel-config {
  background: var(--bg-primary);
  overflow-y: auto;
}

.config-json {
  padding: 12px;
}

.json-editor {
  width: 100%;
  min-height: 400px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  font-family: monospace;
  font-size: 11px;
  color: var(--text-primary);
  resize: vertical;
  outline: none;
}

.json-editor:focus {
  border-color: var(--accent);
}

.config-sections {
  padding: 0;
}

.config-section {
  border-bottom: 1px solid var(--border);
}

.config-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--bg-secondary);
}

.config-section-header:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.config-section-header svg {
  width: 14px;
  height: 14px;
  transition: transform 0.2s;
}

.config-section-header svg.rotated {
  transform: rotate(180deg);
}

.config-section-body {
  padding: 12px 16px;
}

.form-group {
  margin-bottom: 12px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.form-input, .form-textarea {
  width: 100%;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 13px;
  color: var(--text-primary);
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s;
}

.form-input:focus, .form-textarea:focus {
  border-color: var(--accent);
}

.form-textarea {
  resize: vertical;
  line-height: 1.5;
}

.form-textarea.code {
  font-family: monospace;
  font-size: 11px;
}

.form-textarea.code.large {
  min-height: 200px;
}

/* Colors */
.color-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 8px;
}

.color-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.color-preview {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  border: 1px solid rgba(0,0,0,0.1);
}

.color-info {
  flex: 1;
  min-width: 0;
}

.color-key {
  display: block;
  font-size: 10px;
  color: var(--text-muted);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.color-value {
  width: 100%;
  background: transparent;
  border: none;
  font-size: 12px;
  color: var(--text-primary);
  font-family: monospace;
  outline: none;
  padding: 0;
}

.color-delete {
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  flex-shrink: 0;
  transition: all 0.15s;
}

.color-delete:hover {
  background: #ef4444;
  color: white;
}

.color-delete svg {
  width: 12px;
  height: 12px;
}

.add-color-btn {
  width: 100%;
  padding: 8px;
  background: transparent;
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s;
}

.add-color-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(99, 102, 241, 0.05);
}

.add-color-btn svg {
  width: 14px;
  height: 14px;
}

/* Palette */
.palette-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.palette-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 8px;
}

.palette-presets {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.palette-preset {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s;
  font-size: 11px;
  color: var(--text-secondary);
}

.palette-preset:hover {
  border-color: var(--accent);
  background: var(--bg-tertiary);
}

.palette-swatches {
  display: flex;
  gap: 2px;
}

.palette-swatches div {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

/* Page Types */
.page-types-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-bottom: 12px;
}

.page-type-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 6px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
}

.page-type-card:hover {
  border-color: var(--accent);
  background: var(--bg-tertiary);
}

.page-type-card.active {
  border-color: var(--accent);
  background: rgba(99, 102, 241, 0.1);
}

.pt-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.pt-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
  text-transform: capitalize;
}

.pt-placeholders {
  font-size: 10px;
  color: var(--text-muted);
}

.add-page-type-btn {
  grid-column: span 3;
  padding: 8px;
  background: transparent;
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  transition: all 0.15s;
}

.add-page-type-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.add-page-type-btn svg {
  width: 14px;
  height: 14px;
}

.page-type-editor {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-top: 8px;
}

.pte-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: capitalize;
}

/* ===================== Modals ===================== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  width: 480px;
  max-width: 90vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.4);
  animation: modalIn 0.2s ease;
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.modal.modal-sm {
  width: 360px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-header h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.modal-close {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.modal-close:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-close svg {
  width: 16px;
  height: 16px;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
}

/* Save Modal */
.save-preview {
  margin-top: 16px;
}

.sp-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.sp-card {
  height: 100px;
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid rgba(255,255,255,0.1);
}

.sp-name {
  font-size: 18px;
  font-weight: 700;
}

.sp-desc {
  font-size: 12px;
}

/* Color picker */
.color-picker-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.color-input {
  width: 44px;
  height: 38px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  padding: 2px;
  background: var(--bg-tertiary);
}

/* ===================== Buttons ===================== */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  font-family: inherit;
}

.btn svg {
  width: 16px;
  height: 16px;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.85;
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-sm {
  padding: 6px 10px;
  font-size: 12px;
}

.btn-sm svg {
  width: 14px;
  height: 14px;
}

/* ===================== Scrollbar ===================== */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(128, 128, 128, 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(128, 128, 128, 0.4);
}
</style>
