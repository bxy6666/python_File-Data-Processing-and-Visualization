# 项目上下文缓存

## 1. 项目基本信息

- 项目名称：python_File-Data-Processing-and-Visualization
- 项目根目录：E:\PythonProject\PXY666\python_File-Data-Processing-and-Visualization
- 项目类型：混合型项目（Flask 后端 + 原生 HTML/CSS/JavaScript 前端）
- 当前阶段：项目骨架初始化完成，可进入成员功能接入
- 主要目标：完成交互式数据分析系统的上传、清洗、分析、可视化、导出流程
- 当前前端品牌：DataFlow
- 当前前端形态：多页面流程向导式工作台，右侧响应详情常显用于开发期联调
- 项目级规则：存在，优先遵守 `AGENTS.md`

## 2. 技术栈结论

- Web 后端：Flask
- 数据处理：后续由成员A/B接入 Pandas、NumPy
- 可视化：Plotly / Plotly.js
- 机器学习：后续由成员C接入 scikit-learn K-Means
- 前端：HTML、CSS、JavaScript、Fetch API
- 包管理：pip + requirements.txt
- 不使用：React、Vue、Django、MySQL、shadcn/ui、大型 UI 框架

## 3. 关键目录

- `app/__init__.py`：Flask 应用工厂
- `app/routes.py`：多页面路由与 API 路由
- `app/templates/layout.html`：多页面共享布局（侧边栏 + 顶部栏）
- `app/templates/dashboard.html`：工作台总览页
- `app/templates/documents.html`：数据管理 / 上传页
- `app/templates/workflow.html`：清洗、分析、导出流程页
- `app/templates/visualization.html`：Plotly 图表分析页
- `app/static/css/style.css`：多页面工作台样式
- `app/static/js/main.js`：各页面 Fetch 与 Plotly 入口
- `app/utils/`：成员功能接入预留工具模块
- `docs/`：项目上下文与 AI 修改记录

## 4. API 契约

- `GET /`：重定向到 `/dashboard`
- `GET /dashboard`：工作台总览页
- `GET /documents`：数据管理页
- `GET /workflow`：清洗、分析、导出流程页
- `GET /visualization`：图表分析页
- `POST /api/upload`：成员A接入，当前返回 `NOT_IMPLEMENTED`
- `POST /api/clean`：成员B接入，当前返回 `NOT_IMPLEMENTED`
- `POST /api/analyze`：成员C接入，当前返回 `NOT_IMPLEMENTED`
- `GET /api/visualize?chart=<type>`：图表入口，前端只提交图表类型；当前无数据时返回 `DATA_NOT_READY`，并预留 `description` 用于自动图表说明
- `GET /api/export`：成员A接入，当前返回 `NOT_IMPLEMENTED`

## 5. 验证建议

- 启动：`python run.py`
- 首页：访问 `http://127.0.0.1:5000/dashboard`
- 多页面：访问 `/dashboard`、`/documents`、`/workflow`、`/visualization`
- 接口：用 Flask test client 或浏览器开发者工具验证占位响应

## 6. 工具状态

- fd：可用
- ripgrep：可用
- Context7：本次未使用
- ast-grep：本次未使用
- shadcn/ui：不适用
- Aider：本次未使用

## 7. 最近一次初始化结论

- 时间：2026-06-02
- 类型：项目级最小初始化
- 结论：PASS
- 当前是否可进入业务开发：YES
