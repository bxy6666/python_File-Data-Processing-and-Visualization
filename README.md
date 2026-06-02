# DataFlow 交互式数据分析系统

本项目是 Python 课程实验的 Flask 可运行骨架，前端使用原生 HTML/CSS/JavaScript，图表入口预留给 Plotly。当前分工为：成员 A 负责整体框架、前端界面、后端路由与接口调度；成员 B 负责数据读取、数据导出以及缺失值、重复值、异常值等数据清洗；成员 C 负责图表可视化；成员 D 负责数据分析与机器学习部分。

## 本地运行

```powershell
pip install -r requirements.txt
python run.py
```

默认访问：

- 工作台：`http://127.0.0.1:5000/dashboard`
- 数据管理：`http://127.0.0.1:5000/documents`
- 处理流程：`http://127.0.0.1:5000/workflow`
- 图表分析：`http://127.0.0.1:5000/visualization`

## 统一响应格式

所有 JSON 接口统一返回：

```json
{
  "status": "success",
  "code": "UPLOAD_OK",
  "message": "上传成功",
  "data": {}
}
```

失败响应保持同样结构：

```json
{
  "status": "error",
  "code": "DATA_NOT_READY",
  "message": "请先上传数据",
  "data": {}
}
```

字段说明：

- `status`：`success` 或 `error`
- `code`：机器可读状态码，前端用它判断提示
- `message`：给用户看的提示
- `data`：接口数据、摘要、状态或调试信息

## 数据状态

开发期使用 `app/utils/data_store.py` 保存单用户临时状态：

- `raw_dataset`：上传后的原始数据
- `cleaned_dataset`：清洗后的数据
- `analysis_result`：聚类分析结果
- `metadata`：上传、清洗、分析摘要

后续如需多用户或持久化，应替换为 SQLite、本地文件缓存或会话隔离的数据层。

## 接口说明

### 1. 上传数据

`POST /api/upload`

请求类型：`multipart/form-data`

参数：

- `file`：CSV、XLS 或 XLSX 文件

PowerShell 示例：

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/upload -F "file=@data.csv"
```

当前状态：

- 路由已接入 `app/utils/file_utils.py`
- 需要成员 B 实现 `read_uploaded_file(file)`

成员 B 期望返回：

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

上传实现约定：

1. `file` 是 Flask/Werkzeug 的 `FileStorage` 对象，可通过 `file.filename` 读取文件名，通过 `file.stream` 或 `file.read()` 读取内容。
2. `dataset` 会被保存为 `raw_dataset`，后续会原样传给 `clean_dataframe(dataframe, rules)`。
3. `metadata` 建议至少包含 `filename`、`rows`、`columns`，前端和响应详情会直接展示这些信息。
4. 不支持的格式、空文件、解析失败统一 `raise ValueError("错误说明")`，路由会返回 `INVALID_FILE`。
5. 如果成员 B 使用 Pandas 读取 CSV/Excel，需要在 `requirements.txt` 补充对应依赖，例如 `pandas`；读取 `.xlsx` 通常还需要 `openpyxl`。

成功响应示例：

```json
{
  "status": "success",
  "code": "UPLOAD_OK",
  "message": "上传成功",
  "data": {
    "file": {
      "filename": "data.csv",
      "rows": 100,
      "columns": ["col1", "col2"]
    },
    "state": {}
  }
}
```

### 2. 数据清洗

`POST /api/clean`

请求类型：`application/json`

请求体：

```json
{
  "drop_missing": true,
  "drop_duplicates": true,
  "handle_outliers": false
}
```

PowerShell 示例：

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/clean -H "Content-Type: application/json" -d "{\"drop_missing\":true,\"drop_duplicates\":true,\"handle_outliers\":false}"
```

当前状态：

- 路由已接入 `app/utils/clean_utils.py`
- 需要成员 B 实现 `clean_dataframe(dataframe, rules)`
- 调用前必须已有 `raw_dataset`

成员 B 期望返回：

```python
{
    "dataset": cleaned_dataframe,
    "summary": {
        "removed_rows": 0,
        "filled_values": 0
    }
}
```

清洗实现约定：

1. `dataframe` 来自上传接口返回的 `dataset`。
2. `rules` 对应前端三个勾选项：`drop_missing`、`drop_duplicates`、`handle_outliers`。
3. 清洗失败或规则不合法统一 `raise ValueError("错误说明")`，路由会返回 `INVALID_CLEAN_RULES`。
4. 返回的 `dataset` 会保存为 `cleaned_dataset`，后续传给分析和可视化流程。

### 3. K-Means 分析

`POST /api/analyze`

请求类型：`application/json`

请求体：

```json
{
  "method": "kmeans",
  "k": 3
}
```

PowerShell 示例：

```powershell
curl.exe -X POST http://127.0.0.1:5000/api/analyze -H "Content-Type: application/json" -d "{\"method\":\"kmeans\",\"k\":3}"
```

当前状态：

- 路由已接入 `app/utils/ml_utils.py`
- 需要成员 D 实现 `run_kmeans(dataframe, k)`
- 调用前必须已有 `cleaned_dataset`

成员 D 期望返回：

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

分析实现约定：

1. `dataframe` 来自清洗接口返回的 `dataset`。
2. `method` 当前只支持 `kmeans`，其他值会返回 `INVALID_ANALYZE_METHOD`。
3. `k` 已在路由中转为整数，并确保不小于 2。
4. 参数不合法或分析失败统一 `raise ValueError("错误说明")`，路由会返回 `INVALID_ANALYZE_PARAMS`。
5. 返回的 `result` 会保存为 `analysis_result`，后续可供可视化和导出使用。

### 4. 生成图表

`GET /api/visualize?chart=<type>`

支持的 `chart`：

- `bar`
- `line`
- `scatter`
- `box`

PowerShell 示例：

```powershell
curl.exe "http://127.0.0.1:5000/api/visualize?chart=scatter"
```

当前状态：

- 图表入口在 `app/utils/chart_utils.py`
- 当前只校验图表类型和数据状态
- 需要成员 C 实现图表生成、Plotly `figure` 和图表说明
- 后续应返回 Plotly 可直接渲染的 `figure`

未来成功响应建议：

```python
(
    {
        "status": "success",
        "code": "VISUALIZE_OK",
        "message": "图表已创建",
        "data": {
            "figure": {
                "data": [],
                "layout": {}
            },
            "description": "图表说明",
            "fields": []
        }
    },
    200
)
```

可视化实现约定：

1. 前端只提交 `chart`，字段选择由可视化逻辑根据 `cleaned_dataset` 或 `analysis_result` 自动决定。
2. `figure` 必须是 Plotly.js 可直接渲染的结构，至少包含 `data`，可选 `layout`。
3. `description` 用于展示图表说明。
4. `fields` 可选，用于说明实际使用了哪些数据字段。
5. `create_chart_response(...)` 需要返回 `(payload, http_status)`，不要直接返回 Flask response。
6. 不支持的图表类型继续返回 `INVALID_CHART`，不要在前端重新增加 x/y 字段输入。

### 5. 导出结果

`GET /api/export?type=<type>`

支持的 `type`：

- `cleaned`：导出清洗后的数据
- `result`：导出分析结果

PowerShell 示例：

```powershell
curl.exe "http://127.0.0.1:5000/api/export?type=cleaned"
```

当前状态：

- 路由已接入 `app/utils/file_utils.py`
- 需要成员 B 实现 `export_dataset(export_type, state)`
- `cleaned` 需要已有 `cleaned_dataset`
- `result` 需要已有 `analysis_result`

导出实现约定：

1. `export_type` 只会是 `cleaned` 或 `result`。
2. `state` 来自 `app/utils/data_store.py`，包含 `raw_dataset`、`cleaned_dataset`、`analysis_result` 和 `metadata`。
3. 当前路由按统一 JSON 响应返回导出结果，`export_dataset` 可返回 `{"filename": "...", "path": "..."}` 或 `{"content": "..."}` 等 dict。
4. 导出失败统一 `raise ValueError("错误说明")`，路由会返回 `INVALID_EXPORT`。

## 成员接入位置

- 成员 A：整体框架、前端界面、后端路由与接口调度
  - `run.py`
  - `app/__init__.py`
  - `app/routes.py`
  - `app/templates/`
  - `app/static/`
  - `app/utils/response_utils.py`
  - `app/utils/data_store.py`
- 成员 B：数据读取、导出与清洗
  - `app/utils/file_utils.py`
  - `read_uploaded_file(file)`
  - `export_dataset(export_type, state)`
  - `app/utils/clean_utils.py`
  - `clean_dataframe(dataframe, rules)`
- 成员 C：图表可视化
  - `app/utils/chart_utils.py`
  - `create_chart_response(chart, cleaned_dataset, analysis_result)`
- 成员 D：数据分析与机器学习
  - `app/utils/ml_utils.py`
  - `run_kmeans(dataframe, k)`

接入原则：

1. 不改已有 API 路径。
2. 成功和失败都使用统一响应格式。
3. 工具函数优先返回普通 Python 对象或 dict，不直接操作前端页面。
4. 需要新增字段时放入 `data` 内，避免新增顶层字段。
