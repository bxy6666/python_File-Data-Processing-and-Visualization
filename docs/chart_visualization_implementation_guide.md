# 图表呈现实现操作文档

本文档说明 DataFlow 最后一部分“图表分析”应如何落地，重点回答四件事：

1. 四个图分别从哪里获取数据。
2. 图表生成函数应该写在哪里。
3. 后端如何读取当前文件的清洗数据和分析结果。
4. 前端如何接收 Plotly figure 并展示。

## 1. 当前图表链路

现有链路已经搭好，不需要新增 API 路径：

```text
用户进入 /visualization
  ↓
点击柱状图 / 折线图 / 散点图 / 箱线图
  ↓
app/static/js/main.js 读取 #chart-type
  ↓
GET /api/visualize?chart=<bar|line|scatter|box>
  ↓
app/routes.py 调用 create_chart_response(chart, get_cleaned_dataset(), get_analysis_result())
  ↓
app/utils/chart_utils.py 生成 Plotly figure、description、fields
  ↓
前端 Plotly.react(...) 渲染到 #chart
```

因此，成员 C 只需要重点实现：

```text
app/utils/chart_utils.py
```

通常不需要修改：

- `app/routes.py`
- `app/templates/visualization.html`
- `app/static/js/main.js`

除非后续要新增图表类型、字段选择器或交互控件。

## 2. 数据从哪里来

图表接口入口在 `app/routes.py`：

```python
@bp.get("/api/visualize")
def visualize_data():
    chart = request.args.get("chart", "scatter")
    payload, http_status = create_chart_response(chart, get_cleaned_dataset(), get_analysis_result())
    return json_response(payload, http_status)
```

这里有两个关键数据：

- `cleaned_dataset`：由 `get_cleaned_dataset()` 读取，类型是 Pandas `DataFrame`。
- `analysis_result`：由 `get_analysis_result()` 读取，类型是成员 D 的 K-Means 结果字典。

它们都来自 SQLite：

```text
instance/dataflow.sqlite3
```

读取过程已经由 `app/utils/data_store.py` 封装：

```text
get_cleaned_dataset()
  -> 读取当前 active_dataset_id
  -> 查询 dataset_runs.cleaned_dataset
  -> pickle.loads(...) 还原为 DataFrame

get_analysis_result()
  -> 读取当前 active_dataset_id
  -> 查询 dataset_runs.analysis_result
  -> pickle.loads(...) 还原为 dict
```

成员 C 不需要直接连接 SQLite，也不需要自己读取文件。只在 `create_chart_response(chart, cleaned_dataset, analysis_result)` 中使用传入的数据即可。

## 3. 函数写入哪里

所有图表生成逻辑写入：

```text
app/utils/chart_utils.py
```

建议在现有 `create_chart_response(...)` 下方新增辅助函数：

```python
from .response_utils import error_payload, success_payload


def _numeric_columns(dataframe):
    ...


def _analysis_columns(analysis_result):
    ...


def _label_map(analysis_result):
    ...


def _build_bar_figure(cleaned_dataset, analysis_result):
    ...


def _build_line_figure(cleaned_dataset):
    ...


def _build_scatter_figure(cleaned_dataset, analysis_result):
    ...


def _build_box_figure(cleaned_dataset, analysis_result):
    ...
```

然后在 `create_chart_response(...)` 中按 `chart` 分发：

```python
builders = {
    "bar": _build_bar_figure,
    "line": _build_line_figure,
    "scatter": _build_scatter_figure,
    "box": _build_box_figure,
}

figure, description, fields = builders[chart](cleaned_dataset, analysis_result)
return (
    success_payload(
        "VISUALIZE_OK",
        "图表已创建",
        {
            "figure": figure,
            "description": description,
            "fields": fields,
        },
    ),
    200,
)
```

注意：`chart_utils.py` 不要直接 `jsonify`，也不要返回 Flask response。它只返回 `(payload, http_status)`，由 `routes.py` 统一包装。

## 4. 四个图分别用什么数据

### 4.1 柱状图 bar

优先数据来源：

```text
analysis_result["clusters"]
```

该字段来自 K-Means 分析函数 `run_kmeans(...)`，结构大致是：

```python
[
    {"cluster": 0, "count": 12, "center": {...}},
    {"cluster": 1, "count": 18, "center": {...}},
]
```

建议用途：

- x 轴：`cluster 0`、`cluster 1`、`cluster 2`
- y 轴：每个聚类的 `count`
- 图表含义：展示每个聚类类别中的样本数量

如果还没有分析结果，但已经有清洗数据：

- 从 `cleaned_dataset` 中找第一个文本/类别列。
- 使用 `value_counts().head(20)` 统计出现次数。
- x 轴为类别值，y 轴为数量。

适合写入函数：

```python
def _build_bar_figure(cleaned_dataset, analysis_result):
    ...
```

返回的 `fields` 建议：

```python
["analysis_result.clusters.cluster", "analysis_result.clusters.count"]
```

或回退时：

```python
[category_column, "count"]
```

### 4.2 折线图 line

主要数据来源：

```text
cleaned_dataset
```

建议字段选择规则：

1. 先找日期/年份/时间字段，例如列名包含 `date`、`time`、`year`、`日期`、`年份`。
2. 如果找到，将它作为 x 轴。
3. y 轴使用第一个数值列。
4. 如果没有时间字段，x 轴使用 DataFrame 行号，y 轴仍使用第一个数值列。

适合用途：

- 展示某个数值字段随时间或样本顺序变化的趋势。
- 例如电影数据中可用 `release_year` 做 x 轴，`revenue`、`popularity` 或 `vote_average` 做 y 轴。

适合写入函数：

```python
def _build_line_figure(cleaned_dataset):
    ...
```

返回的 `fields` 建议：

```python
[x_column_or_index, y_column]
```

### 4.3 散点图 scatter

优先数据来源：

```text
cleaned_dataset + analysis_result["labels"]
```

建议字段选择规则：

1. 如果有 `analysis_result["columns"]`，优先取其中前两个数值字段作为 x/y。
2. 如果没有分析结果，则从 `cleaned_dataset.select_dtypes(include=["number"])` 取前两个数值列。
3. 如果有 `analysis_result["labels"]`，按 `row_index` 把每行对应的 cluster 映射回来，用 cluster 做颜色。
4. 如果没有分析结果，散点图不分组，只展示两个数值字段关系。

`analysis_result["labels"]` 结构大致是：

```python
[
    {"row_index": "0", "cluster": 1},
    {"row_index": "1", "cluster": 0},
]
```

适合用途：

- 展示两个数值指标之间的关系。
- 分析完成后可以用颜色区分 K-Means 聚类结果。

适合写入函数：

```python
def _build_scatter_figure(cleaned_dataset, analysis_result):
    ...
```

返回的 `fields` 建议：

```python
[x_column, y_column, "cluster"]
```

### 4.4 箱线图 box

主要数据来源：

```text
cleaned_dataset
```

如果已有分析结果，可叠加使用：

```text
analysis_result["labels"]
```

建议字段选择规则：

1. 优先选 `analysis_result["columns"]` 中的第一个数值字段作为 y 轴。
2. 如果没有分析结果，则选 `cleaned_dataset` 中前 1 到 5 个数值列。
3. 如果有聚类标签，则按 cluster 分组画箱线图。
4. 如果没有聚类标签，则每个数值字段画一个箱线图。

适合用途：

- 展示数值字段分布。
- 对比不同聚类类别的数据离散程度。
- 观察异常值。

适合写入函数：

```python
def _build_box_figure(cleaned_dataset, analysis_result):
    ...
```

返回的 `fields` 建议：

```python
[numeric_column, "cluster"]
```

或无分析结果时：

```python
[numeric_column_1, numeric_column_2, ...]
```

## 5. Plotly figure 返回格式

前端现在使用的是：

```javascript
Plotly.react(chartEl, responseData.figure.data, responseData.figure.layout || {}, { responsive: true });
```

所以后端返回的 `figure` 必须是 Plotly.js 能直接识别的普通 dict：

```python
{
    "data": [
        {
            "type": "bar",
            "x": ["cluster 0", "cluster 1"],
            "y": [12, 18],
            "name": "样本数量"
        }
    ],
    "layout": {
        "title": {"text": "各聚类样本数量"},
        "xaxis": {"title": {"text": "聚类类别"}},
        "yaxis": {"title": {"text": "样本数量"}},
        "margin": {"l": 48, "r": 24, "t": 56, "b": 48}
    }
}
```

可以手写 dict，也可以使用 `plotly.graph_objects`：

```python
import plotly.graph_objects as go

fig = go.Figure(...)
figure = fig.to_plotly_json()
```

项目 `requirements.txt` 已包含：

```text
plotly>=5.20,<6.0
```

所以推荐用 `plotly.graph_objects`，结构更清晰。

## 6. 最小实现顺序

建议按下面顺序实现，便于逐步验证：

1. 在 `chart_utils.py` 引入 `success_payload`。
2. 新增 `_numeric_columns(...)`，只负责取数值列。
3. 先实现 `_build_bar_figure(...)`，优先用 `analysis_result["clusters"]`。
4. 修改 `create_chart_response(...)`，让 `chart == "bar"` 能返回成功响应。
5. 用浏览器或 curl 验证柱状图。
6. 再实现 `scatter`，因为它最能体现 K-Means 结果。
7. 再实现 `line` 和 `box`。
8. 最后补单元测试或接口测试。

不要一次性改前端、路由和数据存储。当前接口已经够用。

## 7. 推荐错误处理

在 `chart_utils.py` 中保留现有错误响应：

- 不支持图表类型：`INVALID_CHART`
- 数据未准备：`DATA_NOT_READY`

建议新增或复用：

```python
error_payload(
    "INVALID_CHART_DATA",
    "当前数据缺少生成该图表所需的数值字段",
    {"request": {"chart": chart}},
)
```

常见判断：

- `cleaned_dataset is None` 且 `analysis_result is None`：返回 `DATA_NOT_READY`。
- 折线图、散点图、箱线图找不到数值列：返回 `INVALID_CHART_DATA`。
- 散点图只有 1 个数值列：可以用行号做 x 轴，也可以返回错误；课程演示建议用行号回退，减少验收中断。

## 8. 前端如何读取并展示

前端代码已经在 `app/static/js/main.js` 中完成，不需要新增读取逻辑：

```javascript
const params = new URLSearchParams({
  chart: chartTypeInput?.value || "scatter",
});

const { response, data } = await requestJson(`/api/visualize?${params.toString()}`);
const responseData = data.data || {};

if (responseData.figure && chartEl) {
  Plotly.react(chartEl, responseData.figure.data, responseData.figure.layout || {}, { responsive: true });
  chartDescriptionEl.textContent = responseData.description || "图表已创建。";
}
```

也就是说，后端只要返回：

```json
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
}
```

页面就会自动渲染。

## 9. 验证方式

启动项目：

```powershell
python run.py
```

浏览器验证：

1. 打开 `http://127.0.0.1:5000/documents`。
2. 上传 `data/movies_demo_sample.csv`。
3. 打开 `http://127.0.0.1:5000/workflow`。
4. 点击“开始处理”，完成清洗和 K-Means 分析。
5. 打开 `http://127.0.0.1:5000/visualization`。
6. 分别点击柱状图、折线图、散点图、箱线图，再点击“创建图表”。

接口验证：

```powershell
curl.exe "http://127.0.0.1:5000/api/visualize?chart=bar"
curl.exe "http://127.0.0.1:5000/api/visualize?chart=line"
curl.exe "http://127.0.0.1:5000/api/visualize?chart=scatter"
curl.exe "http://127.0.0.1:5000/api/visualize?chart=box"
```

自动测试建议：

```powershell
python -m unittest discover -s tests
python -m compileall app tests
```

如果只改 `chart_utils.py`，至少执行：

```powershell
python -m compileall app
```

## 10. 四图数据来源汇总

| 图表 | 优先数据来源 | 回退数据来源 | 主要字段 | 函数位置 |
| --- | --- | --- | --- | --- |
| 柱状图 bar | `analysis_result["clusters"]` | `cleaned_dataset` 的类别列计数 | `cluster/count` 或 `category/count` | `_build_bar_figure(...)` |
| 折线图 line | `cleaned_dataset` | 无 | 时间/年份/行号 + 第一个数值列 | `_build_line_figure(...)` |
| 散点图 scatter | `cleaned_dataset` + `analysis_result["labels"]` | `cleaned_dataset` 前两个数值列 | x 数值列、y 数值列、cluster | `_build_scatter_figure(...)` |
| 箱线图 box | `cleaned_dataset` + `analysis_result["labels"]` | `cleaned_dataset` 前 1-5 个数值列 | 数值列、cluster | `_build_box_figure(...)` |

## 11. 交接结论

图表呈现的核心不是前端重做，而是在 `app/utils/chart_utils.py` 中把 `cleaned_dataset` 和 `analysis_result` 转成 Plotly figure。

当前最小落地范围：

- 只改 `app/utils/chart_utils.py`。
- 不改 API 路径。
- 不新增前端字段选择器。
- 不直接读取 SQLite。
- 不直接读取上传文件。
- 不引入新的前端框架。

完成后，`/visualization` 页面会复用现有按钮、Fetch 请求和 `Plotly.react(...)` 自动展示四类图表。
