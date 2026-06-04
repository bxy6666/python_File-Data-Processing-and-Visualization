# DataFlow 项目成员 D 贡献说明

本文件用于说明我在 DataFlow 交互式数据分析系统中完成的数据分析与机器学习模块工作。我的角色主要是把项目中原本预留的机器学习接口，补充为可以真实运行、可以返回结构化分析结果、可以被后续可视化与导出模块继续使用的 K-Means 聚类分析功能。

我主要完成了 K-Means 聚类算法接入、数值字段自动选择、缺失样本防御性处理、特征标准化、聚类结果结构设计、依赖补充和单元测试编写。通过这些工作，项目从“只具备分析接口占位”推进到了“具备真实机器学习分析能力”的阶段。

此外，我还对前端显示做了调整，使聚类摘要与图表更好地适配后端返回的 `summary` 字段和 `labels` 格式，减少前端对内部 `result` 结构的依赖并提升展示一致性。

---

## 1. 负责范围

负责的内容主要包括：

- 数据分析与机器学习模块实现
- K-Means 聚类算法接入
- 清洗后数据的数值字段筛选
- 聚类前的数据有效性校验
- 缺失样本的防御性处理
- 聚类特征标准化
- 聚类中心、类别标签和分析摘要生成
- 分析结果与项目统一接口格式适配
- 机器学习依赖补充
- 机器学习模块单元测试编写
- 验收答辩相关说明文档整理
 - 对前端展示（摘要与图表）进行了适配与调整，使前端直接消费 `summary` 和 `labels` 字段

没有直接实现的内容：

- 文件上传和 CSV/Excel 读取逻辑
- 缺失值、重复值、异常值等清洗规则的具体实现
- Plotly 图表生成逻辑
- 前端页面布局和交互框架
- SQLite 状态存储底层实现
- 多用户登录、权限管理和线上部署

这些内容由其他成员负责，我的模块通过项目已经约定好的接口与它们协作。

---

## 2. 模块位置与调用流程

主要代码位于：

```text
app/utils/ml_utils.py
```

核心函数为：

```python
run_kmeans(dataframe, k)
run_kmeans_predict(input_data, analysis_result)
```

调用与使用场景：

- `run_kmeans`：主要由后端路由（示例：`/api/analyze`）触发，流程为前端提交 `k` → 路由读取清洗后数据 → 调用 `run_kmeans` → 保存 `analysis_result` → 返回分析完成响应。
- `run_kmeans_predict`：用于对新样本进行簇预测，可被后端路由、批处理任务或其他后端模块调用（例如提供预测 API 或在数据导入后自动运行预测）。该函数依赖 `run_kmeans` 的输出（`analysis_result["model"]`）作为预测参数来源。

整体流程示意：

```text
（分析）
用户在前端输入 k 值
        ↓
POST /api/analyze
        ↓
路由检查 method 和 k
        ↓
从 SQLite 中读取 cleaned_dataset
        ↓
调用 run_kmeans(dataframe, k)
        ↓
保存 analysis_result
        ↓
返回 ANALYZE_OK 响应

（预测）
前端或后端任务提供新样本 input_data
        ↓
调用 run_kmeans_predict(input_data, analysis_result)
        ↓
返回 predictions / summary
```

在这个流程中，路由层负责接口调度和统一响应，我的模块负责真正的机器学习分析与预测逻辑。

---

## 3. K-Means 分析函数

下面分别对两个主要函数按相同结构进行说明：输入、参数校验、特殊处理/预处理、实现要点、返回值格式和前端使用建议。

### A. `run_kmeans(dataframe, k)`

1) 输入：

- `dataframe`: Pandas `DataFrame`（或实现 `select_dtypes` 接口的对象），通常来自清洗模块的 `cleaned_dataset`。
- `k`: 可转换为整数的数值类型，指定聚类簇数。

2) 参数校验：

- `k` 必须能转换为 `int`。
- `k >= 2`。
- `k` 不得大于参与聚类的有效样本数量（删除包含参与列缺失值的行后）。

3) 特殊处理 / 预处理：

- 自动选择数值列：`dataframe.select_dtypes(include=["number"])`。
- 删除包含缺失值的样本行：`dropna(axis=0, how="any")`，并记录 `rows_skipped`。

4) 实现要点：

- 使用 `StandardScaler` 对数值特征做标准化，保存 `mean` 与 `scale` 以便后续预测复用。
- 在标准化空间上运行 `KMeans(n_clusters=k, random_state=42, n_init=10)`。
- 将模型簇中心逆标准化（`scaler.inverse_transform`）以获得便于解释的原始尺度中心。

5) 返回值格式：

- 返回 `{ "result": result, "summary": summary }`。
- `result` 包含 `method, k, columns, rows_used, rows_skipped, inertia, clusters, labels, model`（其中 `model` 含 `scaler.mean/scale` 与 `centers_scaled`）。
- `summary` 为前端快速展示摘要，含 `k, columns, rows_used, rows_skipped, inertia, clusters`。

6) 前端使用建议：

- 前端应以 `summary` 为主进行展示（摘要卡、图表）；使用 `labels` 做逐点/逐行标注，只有在需要深度交互或导出时才请求 `result` 的详细字段。

---

### B. `run_kmeans_predict(input_data, analysis_result)`

1) 输入：

- `input_data`: 接受 Pandas `DataFrame`、`list`（多条记录）或 `dict`（单条记录）；函数内部会在必要时用 `pd.DataFrame` 转换。
- `analysis_result`: 来自 `run_kmeans(...)["result"]` 的分析结果或等价字典，必须包含 `model` 子字典（`columns`, `scaler.mean`, `scaler.scale`, `centers_scaled`）。

2) 参数校验：

- 检查 `analysis_result` 含 `model`，并确认 `columns`, `mean`, `scale`, `centers_scaled` 格式与维度一致。
- 检查 `input_data` 是否包含 `model["columns"]` 指定的所有字段，若缺失字段则抛出 `ValueError`。

3) 特殊处理 / 预处理：

- 选择模型字段并删除包含缺失值的行，记录 `rows_received`、`rows_used` 和 `rows_skipped`。
- 尝试将字段转换为数值（`float`），转换失败抛出 `ValueError`。

4) 实现要点：

- 使用 `analysis_result["model"]["mean"]` 与 `scale` 对每行按训练时相同规则进行标准化（处理 `scale==0` 的情形）。
- 在标准化空间中计算样本到每个 `centers_scaled` 的欧氏距离，选取最小距离对应的簇为预测簇；返回距离为欧氏距离的平方根并保留小数位。

5) 返回值格式：

- 返回 `{ "result": result, "summary": summary }`。
- `result` 包含 `method: "kmeans_predict"`, `k`, `columns`, `rows_received`, `rows_used`, `rows_skipped`, `predictions`（每条的 `row_index`, `cluster`, `distance`）和 `clusters`（每簇计数）。
- `summary` 包含 `k, columns, rows_received, rows_used, rows_skipped, clusters`，用于前端展示。

6) 前端使用建议：

- 前端可直接使用 `result.predictions` 绘制预测明细表与按簇统计图；使用 `summary.clusters` 做聚合展示。确保前端表格的索引与 `row_index` 对齐以便高亮或跳转。


---

## 4. 聚类算法实现

### 4.1 特征标准化

使用 scikit-learn 的 `StandardScaler` 对特征进行标准化：

```python
scaler = StandardScaler()
scaled_features = scaler.fit_transform(numeric_dataframe)
```

标准化的原因是不同字段的数值范围可能差异很大。例如销售额可能是几千，利润率可能小于 1。如果直接聚类，数值范围大的字段会主导距离计算。标准化后，各字段可以在相近尺度下参与聚类，使结果更合理。

### 4.2 K-Means 调用

我使用 scikit-learn 的 `KMeans` 实现聚类：

```python
model = KMeans(n_clusters=k, random_state=42, n_init=10)
labels = model.fit_predict(scaled_features)
```

关键参数说明：

- `n_clusters=k`：聚类数量由用户指定。
- `random_state=42`：保证同一份数据多次运行结果稳定，方便验收和测试。
- `n_init=10`：多次初始化，选择更优结果。

### 4.3 聚类中心还原

K-Means 是在标准化后的数据上运行的，但用户更容易理解原始数据尺度。因此将聚类中心从标准化空间还原回原始数值尺度：

```python
centers = scaler.inverse_transform(model.cluster_centers_)
```

最终返回的 `center` 字段使用原始字段数值，便于展示和解释。

---

## 5. 分析结果结构

模块返回符合项目约定的结构：

```python
{
    "result": analysis_result,
    "summary": summary
}
```

其中 `result` 用于保存完整分析结果，`summary` 用于前端和接口响应展示。

### 5.1 result 字段

`result` 中包含：

- `method`：当前方法为 `kmeans`
- `k`：聚类数量
- `columns`：参与聚类的数值字段
- `rows_used`：实际参与聚类的样本数
- `rows_skipped`：被跳过的样本数
- `inertia`：K-Means 惯性值
- `clusters`：每个聚类的样本数量和中心点
- `labels`：每条数据对应的聚类编号

### 5.2 summary 字段

`summary` 中保留前端展示和验收说明最常用的信息：

- `k`
- `columns`
- `rows_used`
- `rows_skipped`
- `inertia`
- `clusters`

这样前端不需要解析完整细节，也能快速展示分析摘要。

我也对前端的显示逻辑提出并实现了小范围调整（前端代码由前端同学合并），使得前端组件直接使用 `summary` 字段进行汇总展示，只有在需要时才访问 `result` 的详细信息，从而降低了前后端耦合。

---

## 6. 与项目其他模块的协作

### 6.1 与清洗模块的协作

该模块依赖清洗模块生成的：

```text
cleaned_dataset
```

如果用户没有先完成数据清洗，路由层会返回 `DATA_NOT_READY`，不会调用机器学习函数。这保证了系统流程顺序清晰。

### 6.2 与状态存储模块的协作

分析完成后，路由层会调用：

```python
set_analysis_result(analysis_result, summary)
```

把分析结果写入 SQLite 状态存储中。这样后续可视化和导出模块可以复用分析结果，而不需要重复运行 K-Means。

### 6.3 与可视化模块的协作

模块返回的 `labels`、`clusters` 和 `center` 可以直接供图表模块使用。例如：

- 散点图可以按聚类标签区分颜色。
- 柱状图可以展示不同 cluster 的样本数量。
- 图表说明可以引用每类中心点解释数据特征。

因此本模块不仅完成分析，还为后续可视化提供了结构化数据基础。

---

## 7. 依赖与环境贡献

为了让机器学习模块可以正常运行，我在 `requirements.txt` 中补充了：

```text
pandas>=2.0,<3.0
scikit-learn>=1.4,<2.0
```

其中：

- `pandas` 用于 DataFrame 数据结构和数值列筛选。
- `scikit-learn` 用于 `StandardScaler` 和 `KMeans`。

模块内部还通过 `_load_sklearn()` 延迟加载机器学习依赖。如果依赖缺失，会返回清晰错误提示，方便其他成员或老师在验收时定位环境问题。

---

## 8. 单元测试贡献

新增了测试目录和测试文件：

```text
tests/__init__.py
tests/test_ml_utils.py
```

测试使用 Python 标准库 `unittest`，不额外引入新的测试框架。

### 8.1 测试覆盖内容

当前测试覆盖了以下情况：

- 正常聚类时返回 `result` 和 `summary`
- 返回结构符合项目接口契约
- 自动选择数值列，忽略文本列
- 含缺失值的行会被跳过
- 聚类中心符合预期
- 每个聚类的样本数量正确
- 每条数据的聚类标签可以返回
- `k` 支持数字字符串
- 非 DataFrame 输入会报错
- 非数字 `k` 会报错
- `k < 2` 会报错
- `k` 大于样本数量会报错
- 没有数值列会报错
- 没有有效数值样本会报错
- 缺少 scikit-learn 依赖时会给出明确错误

### 8.2 测试命令

运行全部测试：

```powershell
python -m unittest discover -v
```

语法编译检查：

```powershell
python -m compileall app tests
```

当前机器学习模块相关测试已经通过，说明模块在正常场景和异常场景下都有基本保障。

---

## 9. 当前完成效果

当前模块已经具备以下能力：

- 可以被 `/api/analyze` 接口调用
- 可以读取清洗后的 DataFrame
- 可以自动筛选数值字段
- 可以处理部分缺失样本
- 可以执行 K-Means 聚类
- 可以返回聚类中心和类别标签
- 可以生成分析摘要
- 可以将结果交给状态存储、可视化和导出流程继续使用
- 有单元测试验证核心逻辑

- 前端显示已根据 `summary` 与 `labels` 字段完成适配，图表和摘要组件能直接消费后端返回的展示字段

这使项目不再只是保留机器学习接口，而是具备了真实的数据分析功能。

---

## 10. 验收时可以说明的技术点

验收时我可以重点说明以下技术点：

1. K-Means 是无监督学习算法，适合对上传后的表格数据进行探索式分组。
2. 算法只处理数值型字段，因此模块会自动筛选数值列。
3. 为了避免字段量纲差异影响距离计算，我使用 `StandardScaler` 做标准化。
4. 为了保证结果稳定，我设置了 `random_state=42`。
5. 为了方便解释，我把聚类中心从标准化空间还原到原始数据尺度。
6. 模块返回的 `labels` 和 `clusters` 可以直接支持后续可视化。
7. 我通过单元测试覆盖了正常和异常情况，保证模块可靠性。

---

## 11. 当前不足与后续改进

当前模块已经能完成 K-Means 聚类分析，但后续还可以继续改进：

- 增加轮廓系数 `silhouette_score`，用于评价聚类效果。
- 增加自动推荐 k 值功能。
- 增加聚类结果的自然语言解释。
- 增加 PCA 降维，让高维数据也能更方便可视化。
- 支持更多机器学习算法，例如 DBSCAN、层次聚类等。
- 增加 `/api/analyze` 的集成测试，验证路由、状态存储和机器学习模块的完整联动。

如果验收时老师问到不足，可以说明当前版本优先保证主流程可运行、算法结果结构清晰、接口稳定、测试覆盖完整，后续可以继续增强算法评价和解释能力。

---

## 12. 个人贡献总结

我的主要贡献是完成 DataFlow 项目的数据分析与机器学习模块，让项目具备真实的 K-Means 聚类能力。

具体来说，我完成了：

- 将 `app/utils/ml_utils.py` 从占位函数改为可运行算法模块。
- 使用 Pandas 自动选择数值列。
- 对缺失样本进行防御性处理。
- 使用 StandardScaler 标准化特征。
- 使用 scikit-learn KMeans 完成聚类。
- 生成聚类中心、类别标签、样本统计和分析摘要。
- 补充 pandas 和 scikit-learn 依赖。
- 编写机器学习模块单元测试。
- 整理验收答辩准备文档。

通过这些工作，我负责的模块已经可以接入项目主流程，为后续图表可视化、结果导出和验收展示提供机器学习分析结果。
