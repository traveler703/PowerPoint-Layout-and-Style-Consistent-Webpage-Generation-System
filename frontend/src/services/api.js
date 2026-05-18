import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// ----------------------------------------
// 项目管理API
// ----------------------------------------

// 获取所有项目
export async function getProjects(params = {}) {
  const response = await apiClient.get('/projects', { params })
  return response.data
}

// 获取单个项目
export async function getProject(projectId) {
  const response = await apiClient.get(`/projects/${projectId}`)
  return response.data
}

// 创建项目
export async function createProject(data) {
  const response = await apiClient.post('/projects', data)
  return response.data
}

// 更新项目
export async function updateProject(projectId, data) {
  const response = await apiClient.put(`/projects/${projectId}`, data)
  return response.data
}

// 删除项目
export async function deleteProject(projectId) {
  const response = await apiClient.delete(`/projects/${projectId}`)
  return response.data
}

// 搜索项目
export async function searchProjects(keyword) {
  const response = await apiClient.get('/projects/search', { params: { q: keyword } })
  return response.data
}

// ----------------------------------------
// 大纲API
// ----------------------------------------

// 创建大纲
export async function createOutline(data) {
  const response = await apiClient.post('/outlines', data)
  return response.data
}

// 获取大纲
export async function getOutline(outlineId) {
  const response = await apiClient.get(`/outlines/${outlineId}`)
  return response.data
}

// 更新大纲
export async function updateOutline(outlineId, data) {
  const response = await apiClient.put(`/outlines/${outlineId}`, data)
  return response.data
}

// 获取项目的所有大纲
export async function getProjectOutlines(projectId) {
  const response = await apiClient.get(`/projects/${projectId}/outlines`)
  return response.data
}

// ----------------------------------------
// PPT生成API
// ----------------------------------------

// 生成大纲
export async function generateOutline(data) {
  const response = await apiClient.post('/generate-outline', data)
  return response.data
}

// 生成预览
export async function generatePreview(data) {
  const response = await apiClient.post('/generate-preview', data)
  return response.data
}

// 并行生成PPT（一次性返回所有页面）
export async function generatePPTParallel(data) {
  const response = await apiClient.post('/generate-ppt-parallel', data)
  return response.data
}

// ----------------------------------------
// 生成的PPT管理API
// ----------------------------------------

// 保存PPT
export async function savePPT(data) {
  const response = await apiClient.post('/ppts', data)
  return response.data
}

// 获取PPT
export async function getPPT(pptId) {
  const response = await apiClient.get(`/ppts/${pptId}`)
  return response.data
}

// 获取项目的所有PPT
export async function getProjectPPTs(projectId, params = {}) {
  const response = await apiClient.get(`/projects/${projectId}/ppts`, { params })
  return response.data
}

// ----------------------------------------
// 文本解析API
// ----------------------------------------

// 解析文本内容
export async function parseText(data) {
  const response = await apiClient.post('/parse-text', data)
  return response.data
}

// ----------------------------------------
// 模板生成 API (LLM 驱动)
// ----------------------------------------

// LLM 对话生成模板
export async function llmGenerateTemplate(messages, mode = 'template') {
  const response = await apiClient.post('/llm/chat', {
    messages: messages,
    mode: mode
  })
  return response.data
}

// LLM 单次生成模板
export async function llmGenerateOnce(userDescription) {
  const response = await apiClient.post('/llm/chat', {
    messages: [
      { role: 'user', content: userDescription }
    ],
    mode: 'template'
  })
  return response.data
}

// 保存模板到文件系统
export async function saveTemplateToFile(templateData) {
  const response = await apiClient.post('/templates', { template_data: templateData })
  return response.data
}

// ----------------------------------------
// 系统API
// ----------------------------------------

// 获取模板列表
export async function getTemplates() {
  const response = await apiClient.get('/templates')
  return response.data
}

// 创建模板
export async function createTemplate(data) {
  const response = await apiClient.post('/templates', data)
  return response.data
}

// 更新模板
export async function updateTemplate(templateId, data) {
  const response = await apiClient.put(`/templates/${templateId}`, data)
  return response.data
}

// 删除模板
export async function deleteTemplate(templateId) {
  const response = await apiClient.delete(`/templates/${templateId}`)
  return response.data
}

// 设置默认模板
export async function setDefaultTemplate(templateId) {
  const response = await apiClient.post(`/templates/${templateId}/set-default`)
  return response.data
}

// 数据库连接测试
export async function testDbConnection() {
  const response = await apiClient.get('/db-test')
  return response.data
}

// 健康检查
export async function healthCheck() {
  const response = await apiClient.get('/health')
  return response.data
}

export default {
  // 项目
  getProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  searchProjects,
  // 大纲
  createOutline,
  getOutline,
  updateOutline,
  getProjectOutlines,
  // PPT生成
  generateOutline,
  generatePreview,
  generatePPTParallel,
  // PPT管理
  savePPT,
  getPPT,
  getProjectPPTs,
  // 模板
  getTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  setDefaultTemplate,
  llmGenerateTemplate,
  llmGenerateOnce,
  saveTemplateToFile,
  // 系统
  testDbConnection,
  healthCheck
}
