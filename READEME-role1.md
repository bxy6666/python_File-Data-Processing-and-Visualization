# DataFlow 项目成员 A 贡献说明

本文件用于说明我在 DataFlow 交互式数据分析系统中完成的工作。我的角色不是单独实现某一个算法模块，而是负责把项目整理成一个可以运行、可以展示、可以让其他成员继续接入功能的基础系统。

我主要完成了 Flask 后端框架、多页面前端界面、接口路由、统一响应格式、SQLite 状态存储、成员协作接口和项目文档整理。后续成员 B 的数据读取与清洗、成员 C 的图表可视化、成员 D 的数据分析与机器学习，都可以基于我搭好的结构继续开发。

---

## 1. 我的负责范围

我负责的内容主要包括：

- 项目基础框架搭建
- Flask 页面路由和 API 路由设计
- 前端多页面工作台设计与实现
- 前端交互逻辑编写
- 统一接口响应格式设计
- SQLite 数据状态存储设计与实现
- 成员 B/C/D 功能接入口规划
- README 和项目说明文档整理
- 冗余代码、缓存文件和历史前端结构清理

我没有直接实现的内容：

- 成员 B 的 CSV/Excel 真实读取逻辑
- 成员 B 的缺失值、重复值、异常值清洗逻辑
- 成员 C 的 Plotly 图表生成逻辑
- 成员 D 的 K-Means 聚类算法逻辑
- 多用户登录、权限管理和线上部署

这些部分已经预留好接口，后续成员只需要在对应工具文件中补充业务逻辑。

---

## 2. 项目框架贡献

### 2.1 启动入口

我整理了项目启动入口 `run.py`，让项目可以直接通过：

```powershell
python run.py
```

启动本地服务。

当前启动入口支持：

- 默认端口 `5000`
- 通过 `PORT` 环境变量修改端口
- 通过 `FLASK_DEBUG=0` 关闭调试模式
- 关闭 reloader，方便本地后台验证

这样其他成员在接入功能时，不需要额外配置复杂启动流程。

### 2.2 Flask 应用结构

我整理了 `app/__init__.py`，使用 Flask 应用工厂创建应用，并注册主蓝图。这样项目结构更清晰，后续如果需要增加配置、初始化数据库或测试客户端，也可以继续扩展。

### 2.3 主路由文件

我在 `app/routes.py` 中统一管理页面路由和 API 路由。

页面路由包括：

| 页面 | 地址 | 作用 |
|---|---|---|
| 工作台 | `/dashboard` | 展示整体流程入口 |
| 数据管理 | `/documents` | 上传数据文件 |
| 处理流程 | `/workflow` | 清洗、分析、导出 |
| 图表分析 | `/visualization` | 选择图表类型并展示图表 |

API 路由包括：

| 功能 | 方法 | 地址 |
|---|---|---|
| 上传数据 | POST | `/api/upload` |
| 数据清洗 | POST | `/api/clean` |
| 聚类分析 | POST | `/api/analyze` |
| 创建图表 | GET | `/api/visualize?chart=<type>` |
| 导出结果 | GET | `/api/export?type=<type>` |

路由层只负责参数读取、状态判断、调用对应成员函数和统一返回结果，不把成员 B/C/D 的业务逻辑写死在路由里。

---

## 3. 前端界面贡献

### 3.1 多页面工作台

我把前端从普通演示页面整理为多页面工作台结构，主要文件包括：

```text
app/templates/layout.html
app/templates/dashboard.html
app/templates/documents.html
app/templates/workflow.html
app/templates/visualization.html
app/static/css/style.css
app/static/js/main.js
```

页面结构按用户操作流程组织：

```text
上传数据 -> 清洗设置 -> 聚类分析 -> 图表预览 -> 导出结果
```

这种结构比单页堆叠更清楚，也方便不同成员按模块接入。

### 3.2 共享布局

我实现了 `layout.html` 作为公共布局，统一了：

- 左侧导航栏
- DataFlow 标识
- 页面标题和副标题
- 主内容区域
- 页面脚本插入位置

所有页面都继承这个布局，减少重复代码，也保证界面风格一致。

### 3.3 工作台页面

`dashboard.html` 负责展示完整流程入口。我在页面中加入了：

- 上传数据入口
- 处理流程入口
- 创建图表入口
- 流程状态卡片
- 从上传到导出的步骤提示

用户进入系统后可以快速知道下一步应该做什么。

### 3.4 数据管理页面

`documents.html` 负责文件上传。我完成了：

- CSV / XLS / XLSX 文件选择区域
- 文件格式说明
- 文件名、格式、大小前端展示
- 上传按钮
- 右侧响应详情展示

前端上传字段固定为 `file`，与后端 `request.files.get("file")` 完全对应，成员 B 实现读取逻辑后无需改前端。

### 3.5 处理流程页面

`workflow.html` 负责清洗、分析和导出。我完成了：

- 清洗选项：删除缺失值、删除重复行、检测异常值
- K-Means 参数：只保留 `k` 值
- 导出按钮：导出清洗数据、导出分析结果
- 每一步的状态提示
- 接口响应详情展示

这里有意避免让用户填写复杂字段，降低普通用户的使用门槛。

### 3.6 图表分析页面

`visualization.html` 负责图表创建。我将图表交互设计为只选择图表类型：

- 柱状图
- 折线图
- 散点图
- 箱线图

前端不再要求用户填写 `x 字段`、`y 字段`、`color 字段`。字段选择交给成员 C 根据数据自动处理。这样更符合普通数据工具的使用方式。

图表页还包含：

- Plotly 图表容器
- 图表说明区域
- 响应详情区域

---

## 4. 前端交互逻辑贡献

我在 `app/static/js/main.js` 中完成了主要前端交互逻辑。

主要包括：

- 封装统一请求函数 `requestJson()`
- 封装 JSON POST 请求函数 `postJson()`
- 上传文件时构造 `FormData`
- 选择文件后展示文件名、格式和大小
- 点击清洗按钮后提交清洗规则
- 点击分析按钮后提交 `method=kmeans` 和 `k`
- 点击导出按钮后请求对应导出接口
- 点击图表类型后更新当前图表选择
- 提交图表请求后读取 `data.figure`
- 成员 C 返回 Plotly figure 后，用 `Plotly.react(...)` 渲染图表
- 将每次接口返回展示在右侧响应详情区域

前端请求和后端接口保持一致：

```text
POST /api/upload
POST /api/clean
POST /api/analyze
GET /api/visualize?chart=scatter
GET /api/export?type=cleaned
GET /api/export?type=result
```

---

## 5. 后端接口贡献

### 5.1 上传接口

接口：

```text
POST /api/upload
```

我完成了：

- 读取上传字段 `file`
- 未选择文件时返回 `NO_FILE`
- 调用成员 B 的 `read_uploaded_file(file)`
- 将成员 B 返回的 `dataset` 保存为 `raw_dataset`
- 将上传摘要保存到 SQLite
- 返回统一响应 `UPLOAD_OK`

成员 B 只需要实现文件读取，不需要处理路由和响应格式。

### 5.2 清洗接口

接口：

```text
POST /api/clean
```

我完成了：

- 从 SQLite 读取 `raw_dataset`
- 没有上传数据时返回 `DATA_NOT_READY`
- 读取前端清洗规则
- 调用成员 B 的 `clean_dataframe(dataframe, rules)`
- 将清洗结果保存为 `cleaned_dataset`
- 返回统一响应 `CLEAN_OK`

### 5.3 分析接口

接口：

```text
POST /api/analyze
```

我完成了：

- 校验 `method` 只能是 `kmeans`
- 校验 `k` 必须是整数且不小于 2
- 从 SQLite 读取 `cleaned_dataset`
- 调用成员 D 的 `run_kmeans(dataframe, k)`
- 将分析结果保存为 `analysis_result`
- 返回统一响应 `ANALYZE_OK`

这样成员 D 可以专注算法，不需要重复写参数校验和状态保存。

### 5.4 可视化接口

接口：

```text
GET /api/visualize?chart=<type>
```

我完成了：

- 只接收图表类型 `chart`
- 支持 `bar`、`line`、`scatter`、`box`
- 从 SQLite 读取清洗数据和分析结果
- 调用成员 C 的 `create_chart_response(...)`
- 将成员 C 返回结果统一包装为 JSON response

前端只传图表类型，字段自动选择由成员 C 完成。

### 5.5 导出接口

接口：

```text
GET /api/export?type=<type>
```

我完成了：

- 校验 `type` 只能是 `cleaned` 或 `result`
- 检查 SQLite 中是否已有对应数据
- 调用成员 B 的 `export_dataset(export_type, state)`
- 返回统一响应 `EXPORT_OK`

---

## 6. 统一响应格式贡献

我新增了 `app/utils/response_utils.py`，统一所有接口返回格式。

成功响应：

```json
{
  "status": "success",
  "code": "UPLOAD_OK",
  "message": "上传成功",
  "data": {}
}
```

失败响应：

```json
{
  "status": "error",
  "code": "DATA_NOT_READY",
  "message": "请先上传数据",
  "data": {}
}
```

统一响应格式的作用：

- 前端可以统一解析接口结果
- 响应详情区域可以直接展示 JSON
- 后续成员不用各自设计返回格式
- 调试时可以通过 `code` 快速判断问题

常见状态码包括：

| 状态码 | 含义 |
|---|---|
| `NO_FILE` | 没有选择上传文件 |
| `DATA_NOT_READY` | 前置数据未准备好 |
| `NOT_IMPLEMENTED` | 对应成员功能未接入 |
| `INVALID_FILE` | 文件解析失败 |
| `INVALID_CLEAN_RULES` | 清洗规则不合法 |
| `INVALID_ANALYZE_METHOD` | 分析方法不支持 |
| `INVALID_K` | k 值不合法 |
| `INVALID_CHART` | 图表类型不支持 |
| `INVALID_EXPORT_TYPE` | 导出类型不支持 |

---

## 7. SQLite 状态存储贡献

我实现了 `app/utils/data_store.py`，将流程状态保存到 SQLite。

数据库文件：

```text
instance/dataflow.sqlite3
```

数据表：

```text
data_state
```

保存内容：

- `raw_dataset`
- `cleaned_dataset`
- `analysis_result`
- `metadata`

对外函数：

```python
set_raw_dataset(dataset, metadata=None)
get_raw_dataset()
set_cleaned_dataset(dataset, summary=None)
get_cleaned_dataset()
set_analysis_result(result, summary=None)
get_analysis_result()
get_export_state()
state_summary()
```

当前使用 `sqlite3 + pickle` 保存 Python 对象。这个方案适合课程实验的本地可信环境，可以让 DataFrame、dict、分析结果等对象在不同接口之间流转。

---

## 8. 给后续成员的接入说明

### 成员 B：数据读取、导出与清洗

主要修改：

```text
app/utils/file_utils.py
app/utils/clean_utils.py
```

上传函数返回：

```python
{
    "dataset": dataframe,
    "metadata": {
        "filename": "data.csv",
        "rows": 100,
        "columns": ["col1", "col2"]
    }
}
```

清洗函数返回：

```python
{
    "dataset": cleaned_dataframe,
    "summary": {
        "removed_rows": 0,
        "filled_values": 0
    }
}
```

### 成员 C：图表可视化

主要修改：

```text
app/utils/chart_utils.py
```

成功时返回：

```python
(
    {
        "status": "success",
        "code": "VISUALIZE_OK",
        "message": "图表已创建",
        "data": {
            "figure": {"data": [], "layout": {}},
            "description": "图表说明",
            "fields": []
        }
    },
    200
)
```

其中 `figure` 要兼容 Plotly.js。

### 成员 D：数据分析与机器学习

主要修改：

```text
app/utils/ml_utils.py
```

分析函数返回：

```python
{
    "result": analysis_result,
    "summary": {
        "k": 3,
        "columns": ["col1", "col2"],
        "clusters": []
    }
}
```

---

## 9. 环境和运行说明贡献

我在 README 中补充了环境要求：

- Python 建议 3.10 或以上版本
- 使用 `pip install -r requirements.txt` 安装依赖
- Flask 是当前后端必需依赖
- SQLite 使用 Python 标准库，不需要单独安装
- 图表页通过 CDN 加载 Plotly.js，需要能访问 `https://cdn.plot.ly/`
- 成员 B 后续可补充 `pandas`、`openpyxl`
- 成员 D 后续可补充 `scikit-learn`
- `PORT` 可以修改运行端口
- `FLASK_DEBUG=0` 可以关闭调试模式

运行方式：

```powershell
pip install -r requirements.txt
python run.py
```

访问地址：

```text
http://127.0.0.1:5000/dashboard
```

---

## 10. 文档和项目整理贡献

我整理了以下文档：

- `README.md`：项目总说明、环境要求、接口说明、成员接入方式
- `docs/project-context.md`：项目上下文、技术栈、目录结构和 API 契约
- `docs/change-log-ai.md`：记录项目结构调整和接口变化
- `READEME-role1.md`：成员 A 个人贡献说明

我还完成了以下清理：

- 新增 `.gitignore`
- 忽略 `__pycache__/`
- 忽略 `*.pyc`
- 忽略 SQLite 运行数据库文件
- 删除仓库中的 Python 缓存文件
- 删除历史前端迭代中的移动端样式和冗余说明

---

## 11. 当前完成效果

当前项目已经具备以下基础能力：

- 可以通过 `python run.py` 启动
- 可以访问工作台、数据管理、处理流程和图表分析页面
- 前端能调用上传、清洗、分析、可视化和导出接口
- 接口返回格式统一
- 上传、清洗、分析状态可以写入 SQLite
- 其他成员可以在预留工具模块中继续补充功能
- README 已写清运行环境、接口调用和协作边界

---

## 12. 个人贡献总结

我的主要贡献是完成 DataFlow 项目的基础框架和协作底座，让项目从零散的页面和占位接口，整理成一个结构清晰、流程完整、接口规范、状态可保存、文档可阅读的数据分析系统。

完成这些基础工作后，成员 B 可以继续实现数据读取、导出和清洗；成员 C 可以继续实现 Plotly 图表生成；成员 D 可以继续实现 K-Means 分析。整体前端、路由、状态存储和接口格式已经准备好，后续开发可以直接在当前基础上推进。
