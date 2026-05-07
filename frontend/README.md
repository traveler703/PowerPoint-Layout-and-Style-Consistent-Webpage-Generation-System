# LandPPT 前端 (Vue.js)

基于 Vue 3 + Vite 的 AI PPT 生成系统前端

## 安装依赖

```bash
cd frontend
npm install
```

## 运行开发服务器

```bash
npm run dev
```

前端运行在 http://localhost:5173

API 代理到 http://localhost:5000

## 构建生产版本

```bash
npm run build
```

## 项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.js
    ├── App.vue
    ├── assets/
    │   └── styles/
    │       └── main.css
    ├── components/
    │   ├── ProcessSteps.vue
    │   ├── InputPanel.vue
    │   ├── OutlinePanel.vue
    │   ├── RightPanel.vue
    │   ├── OutlineSlidePreview.vue
    │   └── FullscreenPreview.vue
    └── services/
        └── api.js
```
