# 项目上下文缓存

## 1. 项目基本信息

- 项目名称：python_File-Data-Processing-and-Visualization
- 项目根目录：E:\PythonProject\PXY666\python_File-Data-Processing-and-Visualization
- 项目类型：混合型项目（Flask 后端 + 原生 HTML/CSS/JavaScript 前端）
- 当前阶段：上传、清洗、分析、导出与文件历史联通已完成；图表生成功能待成员C接入
- 主要目标：完成交互式数据分析系统的上传、清洗、分析、可视化、导出流程
- 当前前端品牌：DataFlow
- 当前前端形态：多页面流程向导式工作台，数据管理页使用 DocAI 风格紧凑文件面板，操作反馈改为页面内状态提示，不再展示调试用响应窗口
- 当前 API 格式：统一返回 `status`、`code`、`message`、`data`
- 当前数据状态：使用 `app/utils/data_store.py` 基于 SQLite 保存单用户上传历史和当前处理对象，数据库文件为 `instance/dataflow.sqlite3`
- 当前成员分工：成员A负责框架、前端、后端路由与接口调度；成员B负责数据读取、导出与清洗；成员C负责可视化；成员D负责数据分析与机器学习
- 项目级规则：存在，优先遵守 `AGENTS.md`

## 2. 技术栈结论

- Web 后端：Flask
- 数据存储：SQLite（Python 标准库 `sqlite3`，运行时数据库文件位于 `instance/dataflow.sqlite3`）
- 数据读取、导出与清洗：已由成员B接口落地，使用 Pandas 读取 CSV/Excel、清洗并导出结果
- 可视化：后续由成员C接入 Plotly / Plotly.js 图表生成
- 机器学习：已由成员D接口落地，使用 scikit-learn K-Means
- 前端：HTML、CSS、JavaScript、Fetch API
- 包管理：pip + requirements.txt
- 不使用：React、Vue、Django、MySQL、shadcn/ui、大型 UI 框架

## 2.1 环境要求

- Python：建议 3.10 或以上版本
- 必装依赖：`Flask`
- 当前保留依赖：`plotly`，供成员C后续在 Python 侧生成 Plotly figure
- 前端图表：`visualization.html` 通过 CDN 加载 Plotly.js，需要能访问 `https://cdn.plot.ly/`
- SQLite：使用 Python 标准库 `sqlite3`，无需单独安装数据库
- 可选依赖：成员B读取 CSV/Excel 时可补充 `pandas`、`openpyxl`；成员D实现 K-Means 时可补充 `scikit-learn`
- 运行环境变量：`PORT` 控制端口，`FLASK_DEBUG=0` 关闭调试模式

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
- `src/components/DataFileUploadPanel.vue`：DocAI 风格文件上传面板参考组件，不接入当前 Flask 运行时
- `app/utils/`：成员B/C/D功能接入预留工具模块，以及成员A维护的响应与 SQLite 状态模块
- `docs/`：项目上下文与 AI 修改记录

## 4. API 契约

- `GET /`：重定向到 `/dashboard`
- `GET /dashboard`：工作台总览页
- `GET /documents`：数据管理页
- `GET /workflow`：清洗、分析、导出流程页
- `GET /visualization`：图表分析页
- `POST /api/upload`：上传数据，调用成员B的 `file_utils.read_uploaded_file(file)`；成功后将 `raw_dataset` 写入 SQLite
- `POST /api/clean`：数据清洗，调用成员B的 `clean_utils.clean_dataframe(dataframe, rules)`；需要已有 `raw_dataset`
- `POST /api/analyze`：K-Means 分析，`method` 仅支持 `kmeans`，调用成员D的 `ml_utils.run_kmeans(dataframe, k)`；需要已有 `cleaned_dataset`
- `GET /api/visualize?chart=<type>`：图表入口，前端只提交图表类型；由成员C补充 Plotly `figure` 与图表说明
- `GET /api/datasets`：返回上传历史、当前处理文件和处理状态
- `POST /api/datasets/<id>/activate`：切换当前处理文件
- `DELETE /api/datasets/<id>`：删除指定上传历史及其处理结果
- `GET /api/export?type=<cleaned|result>&dataset_id=<id>`：导出入口，调用成员B的 `file_utils.export_dataset(export_type, state)`；`dataset_id` 可省略，默认导出当前处理对象

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
