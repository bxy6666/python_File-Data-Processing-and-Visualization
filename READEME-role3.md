# DataFlow 项目成员 C 贡献说明

本文件用于说明我在 DataFlow 交互式数据分析系统中完成的工作。我的角色是负责图表可视化模块，在成员 A 搭建好的路由框架和成员 B/D 完成数据清洗与聚类分析之后，将数据结果转化为可交互的 Plotly 图表，并通过统一的响应格式返回给前端渲染。

我主要完成了 `app/utils/chart_utils.py` 的完整实现，包括四种图表类型（柱状图、折线图、散点图、箱线图）的构建逻辑、字段自动选择策略、K-Means 聚类着色支持和完整的错误处理机制。

---

## 1. 我的负责范围

我负责的内容主要包括：

- `app/utils/chart_utils.py` 的完整实现
- 四种图表类型的构建逻辑（柱状图、折线图、散点图、箱线图）
- 图表字段的自动选择策略（对接成员 D 的 `analysis_result`）
- K-Means 聚类标签的颜色映射与多 Trace 分组渲染
- 对外统一接口 `create_chart_response()` 的实现
- 图表类型校验与各类数据异常的错误处理
- 与成员 A 的统一响应格式（`success_payload` / `error_payload`）对接

我没有直接实现的内容：

- 成员 A 的路由层 `/api/visualize` 接口
- 成员 A 的前端 Plotly.js 图表渲染调用（`Plotly.react(...)`）
- 成员 B 的数据清洗逻辑（`cleaned_dataset` 来源）
- 成员 D 的 K-Means 算法逻辑（`analysis_result` 来源）
- 多用户会话管理与 SQLite 状态读写

图表模块只负责接收已处理好的数据，按图表类型完成可视化构建并返回结果，不直接操作 Flask response，也不读取 SQLite 或上传文件。

---

## 2. 模块结构说明

### 2.1 文件路径与定位

```text
app/utils/chart_utils.py
```

本文件是图表可视化的唯一实现文件。对外只暴露一个函数：

```python
create_chart_response(chart, cleaned_dataset, analysis_result)
```

路由层 `routes.py` 在 `/api/visualize` 接口中调用此函数，本文件不直接操作 Flask 的 response，也不调用数据库。

### 2.2 外部依赖

```text
plotly>=5.20,<6.0   （requirements.txt 已包含）
pandas              （成员 B 已引入）
```

### 2.3 支持的图表类型

```python
SUPPORTED_CHARTS = frozenset({"bar", "line", "scatter", "box"})
```

分别对应：柱状图、折线图、散点图、箱线图。

---

## 3. 私有工具函数贡献

我在模块内部实现了四个私有工具函数，为各图表构建函数提供数据预处理支持。

### 3.1 `_numeric_columns(df)`

返回 DataFrame 中所有数值列的列名列表，使用 pandas 的 `select_dtypes` 实现，供折线图、散点图、箱线图使用。

### 3.2 `_analysis_columns(analysis_result)`

从 `analysis_result['columns']` 中提取参与聚类的字段名列表，供散点图和箱线图优先选取字段时使用。

### 3.3 `_label_map(analysis_result)`

将 `analysis_result['labels']` 展开为 `{row_index: cluster_id}` 字典，支持按行映射聚类颜色。

`labels` 的输入结构来自成员 D 的 `run_kmeans` 返回：

```python
[{"row_index": "0", "cluster": 1}, ...]
```

函数中加入了类型转换保护（`int(entry["row_index"])`、`int(entry["cluster"])`），避免成员 D 返回字符串类型时出错。

### 3.4 `_cluster_series(df, analysis_result)`

将 `_label_map` 的结果转换为与 DataFrame 等长的 `pd.Series`，每行对应一个聚类标签，供散点图和箱线图分组使用。若无分析结果则返回 `None`，图表自动回退到无分组模式。

---

## 4. 四种图表构建函数贡献

### 4.1 柱状图 `_build_bar_figure()`

**优先逻辑：** 若 `analysis_result` 包含聚类信息（`clusters` 字段），则展示各聚类的样本数量分布。

**回退逻辑：** 若无聚类结果，则在 `cleaned_dataset` 中寻找第一个文本或类别列，展示该字段的 Top 20 类别频次。

**数据缺失处理：** 若无聚类结果且数据集不含类别列，则抛出 `ValueError("INVALID_CHART_DATA")`，由入口函数统一转换为 `400` 错误响应。

### 4.2 折线图 `_build_line_figure()`

x 轴优先识别列名中含 `date`、`time`、`year`、`日期`、`年份`、`月份`、`时间` 的列，找不到则以行序号作为 x 轴。y 轴取第一个数值列。

折线图不使用聚类结果，保留 `analysis_result` 参数仅为接口统一性。

### 4.3 散点图 `_build_scatter_figure()`

**字段选取优先级：**

1. 优先取 `analysis_result['columns']` 前两个且存在于 DataFrame 中的字段
2. 其次取 DataFrame 前两个数值列
3. 若只有一个数值列，以行序号为 x 轴

**聚类着色：** 若有 `analysis_result['labels']`，则按聚类分组构建多条 Trace，每个聚类使用 `_PALETTE` 调色板中的不同颜色。若无聚类结果，则展示统一颜色的单 Trace 散点。

### 4.4 箱线图 `_build_box_figure()`

**字段选取：** 优先取参与聚类的数值字段（`analysis_result['columns']` 中存在于 DataFrame 的部分），回退取 DataFrame 前 5 个数值字段。

**聚类分组模式：** 若有聚类标签，只展示第一个字段、按聚类分组展示箱线分布，避免图表过于密集。

**无聚类模式：** 展示最多 5 个字段各自的分布情况，可观察各字段中位数、四分位距与异常值。

---

## 5. 调色板设计

我使用 Plotly 默认系列调色板，按聚类顺序循环分配颜色：

```python
_PALETTE = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692"]
```

所有图表统一使用此调色板，保持视觉风格一致。

---

## 6. 对外入口函数贡献

### `create_chart_response(chart, cleaned_dataset, analysis_result)`

这是本模块唯一的对外函数，由 `routes.py` 调用。

**参数：**

| 参数 | 类型 | 来源 |
|---|---|---|
| `chart` | `str` | 前端传入，`bar` / `line` / `scatter` / `box` |
| `cleaned_dataset` | `pd.DataFrame \| None` | 成员 B 清洗结果，来自 `get_cleaned_dataset()` |
| `analysis_result` | `dict \| None` | 成员 D K-Means 结果，来自 `get_analysis_result()` |

**返回：** `(payload_dict, http_status)`，payload 符合成员 A 定义的统一响应格式，由 `routes.py` 通过 `json_response()` 包装后返回给前端。

成功响应示例：

```json
{
  "status": "success",
  "code": "VISUALIZE_OK",
  "message": "图表已创建",
  "data": {
    "figure": {"data": [], "layout": {}},
    "description": "各 K-Means 聚类中的样本数量分布。",
    "fields": ["analysis_result.clusters.cluster", "analysis_result.clusters.count"]
  }
}
```

---

## 7. 错误处理贡献

入口函数中实现了三层错误处理：

### 7.1 图表类型校验

图表类型不在 `SUPPORTED_CHARTS` 中时，返回 `400 INVALID_CHART`：

```json
{
  "status": "error",
  "code": "INVALID_CHART",
  "message": "不支持的图表类型「pie」，支持：bar、line、scatter、box"
}
```

### 7.2 数据就绪检查

`cleaned_dataset` 和 `analysis_result` 均为 `None` 时，返回 `400 DATA_NOT_READY`：

```json
{
  "status": "error",
  "code": "DATA_NOT_READY",
  "message": "请先上传数据并完成清洗，再生成图表"
}
```

### 7.3 图表生成异常

图表构建函数内部可能抛出两类 `ValueError`：

| 错误码 | 触发场景 | HTTP 状态 |
|---|---|---|
| `DATA_NOT_READY` | 数据集为空 | 400 |
| `INVALID_CHART_DATA` | 数据缺少生成图表所需字段 | 400 |

其他未知异常（`Exception`）统一返回 `500 CHART_ERROR`，附带异常信息，方便调试。

---

## 8. 与其他成员的接口约定

### 对接成员 A（路由层）

成员 A 在 `/api/visualize?chart=<type>` 接口中调用本函数：

```python
from .utils.chart_utils import create_chart_response

payload, status = create_chart_response(chart, cleaned_dataset, analysis_result)
return json_response(payload, status)
```

本模块不直接返回 Flask response，完全由成员 A 的路由层包装，职责边界清晰。

### 对接成员 B（数据输入）

本模块使用的 `cleaned_dataset` 来自成员 B 的清洗结果。数据为标准 `pd.DataFrame`，图表模块会自动识别其中的数值列和类别列，不依赖特定列名约定。

### 对接成员 D（聚类结果输入）

本模块使用的 `analysis_result` 来自成员 D 的 K-Means 返回结果。依赖的字段如下：

```python
analysis_result = {
    "columns": ["col1", "col2"],     # 参与聚类的字段
    "labels": [
        {"row_index": "0", "cluster": 1},
        ...
    ],
    "clusters": [
        {"cluster": 0, "count": 42},
        ...
    ]
}
```

以上三个字段均做了空值保护，成员 D 若只返回部分字段，图表模块会自动降级处理，不会报错。

---

## 9. 当前完成效果

目前图表模块已具备以下能力：

- 接收路由层传入的图表类型和数据，生成标准 Plotly JSON
- 柱状图支持聚类数量统计与类别频次两种模式
- 折线图支持自动识别时间列作为 x 轴
- 散点图支持聚类着色分组，字段自动选取优先对接成员 D 的分析列
- 箱线图支持聚类分组展示与多字段对比展示
- 所有图表统一调色板，视觉风格一致
- 图表类型、数据就绪、字段缺失、未知异常四类错误均有对应处理和响应码
- 返回格式与成员 A 的统一响应结构完全兼容，前端可直接用 `Plotly.react()` 渲染 `data.figure`

---

## 10. 个人贡献总结

我的主要贡献是完成 DataFlow 项目的图表可视化模块，将成员 B 的清洗数据和成员 D 的聚类结果转化为四种可交互 Plotly 图表，并通过统一接口返回给前端渲染。

模块在设计上考虑了以下几点：字段自动选取使前端无需传入列名，降低前端复杂度；聚类结果优先兼容但不强制依赖，保证在成员 D 未完成时图表仍可基于原始数据生成；错误处理覆盖了主要异常场景，响应码与成员 A 的状态码体系保持一致，方便前端统一处理。
