# DataFlow 项目成员 B 贡献说明

本文件用于说明我在 DataFlow 交互式数据分析系统中完成的数据读取、数据清洗与结果导出模块工作。我的角色主要是把项目中原本预留的数据处理接口，补充为可以真实读取 CSV/Excel 文件、可以按规则清洗数据、可以导出处理结果的业务模块。

我主要完成了文件格式校验、CSV/Excel 数据读取、中文 CSV 编码兼容、数据元信息生成、缺失值处理、重复行处理、异常值处理、清洗摘要生成、清洗结果导出、分析结果导出和测试补充。通过这些工作，项目从“只保留上传和清洗接口入口”推进到了“可以完成真实数据处理流程”的阶段。

---

## 1. 我的负责范围

我负责的内容主要包括：

- 上传文件格式校验
- CSV 文件读取
- XLS / XLSX 文件读取
- 中文 CSV 常见编码兼容
- 上传数据元数据生成
- 缺失值清洗
- 重复行清洗
- 异常值检测与处理
- 清洗结果摘要生成
- 清洗数据导出
- 分析结果导出
- 数据处理模块测试编写
- 数据清洗模块验收文档整理

我没有直接实现的内容：

- Flask 应用框架和页面路由
- 前端页面布局与 Fetch 交互
- SQLite 状态存储底层实现
- K-Means 聚类算法
- Plotly 图表生成逻辑
- 多用户登录、权限管理和线上部署

这些内容由其他成员负责，我的模块通过项目已有的路由和状态存储接口与它们协作。

---

## 2. 模块位置与接口

我的主要代码位于：

```text
app/utils/file_utils.py
app/utils/clean_utils.py
```

其中：

- `file_utils.py` 负责文件读取与结果导出。
- `clean_utils.py` 负责缺失值、重复值和异常值等清洗逻辑。

对应后端接口为：

```text
POST /api/upload
POST /api/clean
GET /api/export?type=cleaned
GET /api/export?type=result
```

整体调用流程如下：

```text
用户上传 CSV/Excel
        ↓
read_uploaded_file(file)
        ↓
保存 raw_dataset
        ↓
用户选择清洗规则
        ↓
clean_dataframe(dataframe, rules)
        ↓
保存 cleaned_dataset
        ↓
后续分析 / 可视化 / 导出
```

---

## 3. 文件读取模块贡献

### 3.1 支持格式

我实现了对以下格式的读取：

```text
.csv
.xls
.xlsx
```

模块会根据文件扩展名判断格式，不支持的文件会返回明确错误：

```text
仅支持 CSV、XLS 或 XLSX 文件
```

这样可以避免用户上传不符合要求的文件后进入后续流程。

### 3.2 CSV 读取

CSV 文件由 Pandas 读取。考虑到中文环境中 CSV 编码不统一，我加入了多编码尝试：

```python
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030")
```

这样可以兼容：

- UTF-8 CSV
- 带 BOM 的 UTF-8 CSV
- Windows 下常见的 GBK 中文 CSV
- 更完整的 GB18030 中文编码

如果所有编码都不能解析，会返回：

```text
CSV 文件编码无法识别，请使用 UTF-8 或 GBK 编码
```

### 3.3 Excel 读取

Excel 文件根据扩展名分别处理：

- `.xlsx` 使用 `openpyxl`
- `.xls` 使用 `xlrd`

对应依赖已经补充到 `requirements.txt` 中：

```text
openpyxl>=3.1,<4.0
xlrd>=2.0,<3.0
```

如果缺少依赖，模块会提示用户先安装项目依赖。

### 3.4 上传元数据

文件读取成功后，我会返回：

```python
{
    "dataset": dataframe,
    "metadata": {
        "filename": "...",
        "format": "...",
        "rows": 0,
        "column_count": 0,
        "columns": [],
        "missing_values": 0
    }
}
```

这些元数据会被上传接口返回给前端，也会写入数据状态，便于后续流程判断和验收展示。

---

## 4. 数据清洗模块贡献

### 4.1 清洗入口

数据清洗核心函数为：

```python
clean_dataframe(dataframe, rules)
```

其中：

- `dataframe` 来自上传读取后的原始数据。
- `rules` 来自前端清洗选项。

当前支持的规则包括：

```text
drop_missing
drop_duplicates
handle_outliers
```

### 4.2 清洗规则校验

我为清洗规则实现了校验逻辑：

- `rules` 必须是 JSON 对象。
- 不允许出现未知规则。
- 每个规则值必须能解析为布尔值。

这样可以保证清洗模块不会因为异常输入进入不可控状态。

模块还兼容常见字符串布尔值，例如：

```text
true / false
1 / 0
yes / no
on / off
```

### 4.3 缺失值处理

当 `drop_missing` 开启时，模块会删除包含任意缺失值的行：

```python
cleaned_dataframe.dropna(axis=0, how="any")
```

同时记录：

- 清洗前缺失值总数
- 清洗后缺失值总数
- 因缺失值删除的行数

这些数据会进入 `summary`，便于前端展示和验收说明。

### 4.4 重复行处理

当 `drop_duplicates` 开启时，模块会删除完全重复的行：

```python
cleaned_dataframe.drop_duplicates()
```

同时记录：

```text
duplicate_rows_before
removed_duplicate_rows
```

这样用户可以清楚看到重复数据对原始数据规模的影响。

### 4.5 异常值处理

当 `handle_outliers` 开启时，模块使用 IQR 方法检测数值列异常值。

计算方式为：

```text
IQR = Q3 - Q1
下界 = Q1 - 1.5 * IQR
上界 = Q3 + 1.5 * IQR
```

如果某一行在任意数值列中超出上下界，则删除该行。

异常值处理只针对数值列，文本列不会参与计算。

输出摘要中会包含：

```text
outlier_rows_removed
outlier_fields
```

这可以说明删除了多少异常行，以及哪些字段存在异常值。

---

## 5. 清洗摘要结构贡献

清洗完成后，模块返回：

```python
{
    "dataset": cleaned_dataframe,
    "summary": summary
}
```

其中 `summary` 包含：

- `rules`：实际使用的清洗规则
- `input_rows`：输入行数
- `input_columns`：输入列数
- `output_rows`：输出行数
- `output_columns`：输出列数
- `missing_values_before`：清洗前缺失值数量
- `missing_values_after`：清洗后缺失值数量
- `duplicate_rows_before`：清洗前重复行数量
- `removed_missing_rows`：删除的缺失行数量
- `removed_duplicate_rows`：删除的重复行数量
- `outlier_rows_removed`：删除的异常值行数量
- `outlier_fields`：出现异常值的字段
- `removed_rows`：总删除行数
- `filled_values`：填充值数量，目前为 0

这个摘要既可以用于前端展示，也可以用于验收时解释清洗效果。

---

## 6. 导出模块贡献

我实现了：

```python
export_dataset(export_type, state)
```

### 6.1 导出清洗数据

当 `export_type` 为 `cleaned` 时，模块会把 `cleaned_dataset` 转为 CSV 内容：

```python
{
    "filename": "cleaned_dataset.csv",
    "format": "csv",
    "content": "...",
    "rows": 0,
    "columns": []
}
```

### 6.2 导出分析结果

当 `export_type` 为 `result` 时，模块会把 `analysis_result` 转为 JSON 内容：

```python
{
    "filename": "analysis_result.json",
    "format": "json",
    "content": "..."
}
```

当前项目统一使用 JSON 响应返回接口结果，所以导出模块暂时返回文件内容，而不是直接触发浏览器下载。

---

## 7. 与其他模块的协作

### 7.1 与成员 A 框架模块协作

成员 A 已经完成 Flask 路由、统一响应和状态存储接口。我的模块不直接处理 Flask response，而是返回普通 Python 对象，由路由统一包装。

### 7.2 与成员 D 机器学习模块协作

我的清洗模块输出：

```text
cleaned_dataset
```

机器学习模块会基于它执行 K-Means 聚类。因此本模块为后续分析提供了更干净的数据基础。

### 7.3 与成员 C 可视化模块协作

可视化模块可以直接使用清洗后的 DataFrame 生成基础图表，也可以结合机器学习结果展示聚类效果。

### 7.4 与导出流程协作

我的导出函数可以导出清洗后的数据，也可以导出机器学习分析结果，保证完整流程最终可以产生可交付结果。

---

## 8. 测试贡献

我新增了以下测试文件：

```text
tests/test_file_utils.py
tests/test_clean_utils.py
tests/test_data_processing_routes.py
```

### 8.1 文件读取测试

覆盖内容包括：

- UTF-8 CSV 读取
- GBK 中文 CSV 读取
- XLSX 读取
- 不支持格式报错
- 空文件报错
- 只有表头的文件报错

### 8.2 数据清洗测试

覆盖内容包括：

- 删除缺失值
- 删除重复行
- IQR 异常值处理
- 关闭规则时保留对应数据
- 字符串布尔值解析
- 默认规则行为
- 非 DataFrame 输入报错
- 非 JSON 对象规则报错
- 未知规则报错
- 非法布尔值报错

### 8.3 导出和接口测试

覆盖内容包括：

- 清洗数据导出为 CSV
- 分析结果导出为 JSON
- 缺少导出数据时报错
- 上传接口读取 CSV 并返回元数据
- 清洗接口返回清洗摘要
- 导出接口返回 CSV 内容

### 8.4 验证结果

运行命令：

```powershell
python -m unittest discover -v
python -m compileall app tests
```

当前全项目测试通过：

```text
Ran 33 tests
OK
```

---

## 9. 当前完成效果

当前我的模块已经具备以下能力：

- 可以读取 CSV、XLS、XLSX 文件
- 可以兼容中文 CSV 常见编码
- 可以返回上传文件元数据
- 可以删除缺失值行
- 可以删除重复行
- 可以用 IQR 方法处理异常值
- 可以返回完整清洗摘要
- 可以导出清洗后的 CSV 数据
- 可以导出分析结果 JSON
- 可以通过 `/api/upload`、`/api/clean`、`/api/export` 接口进入项目主流程
- 有单元测试和接口测试保障

这使项目的数据处理流程从占位接口变成了可运行的业务功能。

---

## 10. 验收时可以说明的技术点

验收时我可以重点说明以下技术点：

1. 文件读取支持 CSV 和 Excel，覆盖常见课程实验数据格式。
2. CSV 读取兼容 UTF-8、GBK、GB18030，适合中文数据环境。
3. 清洗规则由前端传入，后端会严格校验规则是否合法。
4. 缺失值处理使用删除整行方式，简单直观，适合当前课程项目。
5. 重复行处理使用 Pandas 的 `drop_duplicates()`。
6. 异常值处理使用 IQR 方法，不依赖正态分布，适合基础表格数据。
7. 清洗摘要会记录清洗前后变化，便于用户理解处理效果。
8. 导出模块可以返回清洗数据和分析结果，支撑完整闭环。
9. 模块有独立测试和接口测试，保证功能可靠性。

---

## 11. 当前不足与后续改进

当前模块已经完成基础数据处理功能，但后续仍可以改进：

- 缺失值处理可以增加均值、中位数、众数填充。
- 异常值处理可以支持删除、截断或替换等多种策略。
- 可以支持用户选择具体字段进行清洗。
- 可以增加清洗前后数据预览。
- 可以支持更多格式，例如 TSV、JSON。
- 导出接口可以改为真实文件下载。
- 可以增加清洗日志，让用户看到每一步处理细节。

如果验收时老师问到不足，可以说明：当前版本优先保证上传、清洗、分析、导出的主流程打通，后续可以继续扩展更细粒度的数据清洗策略。

---

## 12. 个人贡献总结

我的主要贡献是完成 DataFlow 项目的数据读取、数据清洗与结果导出模块，让项目具备真实处理用户数据的能力。

具体来说，我完成了：

- `read_uploaded_file(file)` 文件读取函数实现。
- `clean_dataframe(dataframe, rules)` 数据清洗函数实现。
- `export_dataset(export_type, state)` 结果导出函数实现。
- CSV/Excel 格式支持。
- 中文 CSV 编码兼容。
- 缺失值、重复值、异常值清洗。
- 清洗摘要结构设计。
- CSV 和 JSON 导出结果生成。
- 依赖补充。
- 数据处理模块测试补充。
- 数据清洗验收文档整理。

通过这些工作，我负责的模块已经可以接入项目主流程，为后续机器学习分析、图表可视化和结果导出提供稳定的数据基础。
