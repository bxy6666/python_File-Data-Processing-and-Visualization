# 数据读取、清洗与导出模块验收答辩准备文档

## 1. 模块定位

本模块对应 DataFlow 项目中的“数据读取、数据清洗与结果导出”部分，主要负责把用户上传的 CSV 或 Excel 文件转换为 Pandas DataFrame，对数据执行缺失值、重复值和异常值处理，并在后续流程完成后提供清洗数据或分析结果的导出内容。

在系统完整流程中，本模块覆盖第一步、第二步和最后一步：

```text
上传数据 -> 数据清洗 -> K-Means 分析 -> 图表可视化 -> 结果导出
```

对应的核心文件是：

```text
app/utils/file_utils.py
app/utils/clean_utils.py
```

对应的后端接口是：

```text
POST /api/upload
POST /api/clean
GET /api/export?type=<cleaned|result>
```

路由层负责接收请求、检查流程状态、保存数据状态和返回统一 JSON；我的模块负责具体的数据读取、清洗和导出逻辑。

## 2. 我完成的主要工作

本模块目前完成了以下内容：

1. 实现 CSV、XLS、XLSX 文件读取。
2. 支持 CSV 常见编码，包括 UTF-8、UTF-8 BOM、GBK 和 GB18030。
3. 读取文件后返回 Pandas DataFrame 和文件元数据。
4. 实现缺失值删除功能。
5. 实现重复行删除功能。
6. 实现基于 IQR 方法的异常值处理功能。
7. 实现清洗摘要统计，包括输入行数、输出行数、缺失值数量、重复行数量、异常值处理结果等。
8. 实现清洗后数据导出为 CSV 内容。
9. 实现分析结果导出为 JSON 内容。
10. 补充 Excel 读取依赖 `openpyxl` 和 `xlrd`。
11. 编写单元测试和路由测试，验证模块核心行为。

## 3. 数据读取模块说明

### 3.1 入口函数

文件读取入口在：

```python
read_uploaded_file(file)
```

其中 `file` 是 Flask/Werkzeug 的 `FileStorage` 对象，由上传接口传入。

### 3.2 支持的文件格式

当前支持：

```text
.csv
.xls
.xlsx
```

如果用户上传其他格式，例如 `.txt` 或 `.json`，模块会抛出错误：

```text
仅支持 CSV、XLS 或 XLSX 文件
```

### 3.3 CSV 编码处理

CSV 文件在中文环境下经常会遇到编码问题，所以模块按顺序尝试以下编码：

```python
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030")
```

这样既能兼容 UTF-8 文件，也能兼容 Windows 下常见的 GBK 中文 CSV 文件。

### 3.4 Excel 读取处理

Excel 文件根据扩展名选择读取方式：

- `.xlsx` 使用 `openpyxl`
- `.xls` 使用 `xlrd`

如果缺少依赖，会给出明确提示：

```text
缺少 Excel 读取依赖，请先运行 pip install -r requirements.txt
```

### 3.5 上传后返回的元数据

文件读取成功后，模块返回：

```python
{
    "dataset": dataframe,
    "metadata": {...}
}
```

`metadata` 中包含：

- `filename`：原始文件名
- `format`：文件格式
- `rows`：数据行数
- `column_count`：字段数量
- `columns`：字段名列表
- `missing_values`：缺失值总数

这些信息会进入 `/api/upload` 的响应，方便前端展示和调试。

## 4. 数据清洗模块说明

### 4.1 入口函数

数据清洗入口在：

```python
clean_dataframe(dataframe, rules)
```

参数说明：

- `dataframe`：上传读取后的 Pandas DataFrame。
- `rules`：前端传入的清洗规则 JSON。

规则示例：

```json
{
  "drop_missing": true,
  "drop_duplicates": true,
  "handle_outliers": false
}
```

### 4.2 规则校验

当前支持的规则是：

```python
SUPPORTED_RULES = {"drop_missing", "drop_duplicates", "handle_outliers"}
```

如果传入未知规则，模块会拒绝处理并返回错误。例如：

```text
存在不支持的清洗规则：unknown
```

每个规则都必须是布尔值。模块也兼容一些常见字符串形式，例如：

```text
true / false
1 / 0
yes / no
on / off
```

这样可以增强接口容错能力。

### 4.3 删除缺失值

当 `drop_missing` 为 `true` 时，模块会执行：

```python
cleaned_dataframe.dropna(axis=0, how="any")
```

含有任意缺失值的行会被删除。

模块会统计：

- 清洗前缺失值总数
- 清洗后缺失值总数
- 因缺失值删除的行数

对应摘要字段包括：

```text
missing_values_before
missing_values_after
removed_missing_rows
```

### 4.4 删除重复行

当 `drop_duplicates` 为 `true` 时，模块会执行：

```python
cleaned_dataframe.drop_duplicates()
```

完全重复的行会被删除。

模块会统计：

```text
duplicate_rows_before
removed_duplicate_rows
```

### 4.5 异常值处理

当 `handle_outliers` 为 `true` 时，模块使用 IQR 方法检测异常值。

IQR 的计算方式是：

```text
IQR = Q3 - Q1
下界 = Q1 - 1.5 * IQR
上界 = Q3 + 1.5 * IQR
```

如果某一行在任意数值列中超出上下界，就认为该行存在异常值，并删除该行。

模块只对数值型字段执行异常值检测。文本字段不会参与异常值计算。

对应摘要字段包括：

```text
outlier_rows_removed
outlier_fields
```

其中 `outlier_fields` 会记录检测到异常值的字段名。

## 5. 清洗结果输出结构

清洗函数返回结构为：

```python
{
    "dataset": cleaned_dataframe,
    "summary": summary
}
```

`dataset` 是清洗后的 DataFrame，会被路由层保存为：

```text
cleaned_dataset
```

`summary` 是清洗摘要，主要字段包括：

- `rules`：实际使用的清洗规则
- `input_rows`：输入行数
- `input_columns`：输入列数
- `output_rows`：输出行数
- `output_columns`：输出列数
- `missing_values_before`：清洗前缺失值数量
- `missing_values_after`：清洗后缺失值数量
- `duplicate_rows_before`：清洗前重复行数量
- `removed_missing_rows`：因缺失值删除的行数
- `removed_duplicate_rows`：删除的重复行数
- `outlier_rows_removed`：删除的异常值行数
- `outlier_fields`：发现异常值的字段
- `removed_rows`：总删除行数
- `filled_values`：填充值数量，目前为 0

## 6. 导出模块说明

### 6.1 导出入口

导出入口函数为：

```python
export_dataset(export_type, state)
```

其中：

- `export_type` 只支持 `cleaned` 或 `result`
- `state` 来自 `data_store.get_export_state()`

### 6.2 导出清洗数据

当：

```text
export_type = "cleaned"
```

模块会读取：

```text
cleaned_dataset
```

并返回 CSV 内容：

```python
{
    "filename": "cleaned_dataset.csv",
    "format": "csv",
    "content": "...",
    "rows": 100,
    "columns": [...]
}
```

### 6.3 导出分析结果

当：

```text
export_type = "result"
```

模块会读取：

```text
analysis_result
```

并返回 JSON 内容：

```python
{
    "filename": "analysis_result.json",
    "format": "json",
    "content": "..."
}
```

当前导出结果按项目统一 JSON 响应返回，前端会根据响应中的 `filename` 与 `content` 创建 Blob 下载，因此页面上已经具备真实下载体验。

## 7. 与其他模块的协作关系

### 7.1 与前端上传页面协作

前端上传页会把文件放入字段：

```text
file
```

后端 `/api/upload` 读取该字段后调用：

```python
read_uploaded_file(file)
```

因此前后端字段名保持一致。

### 7.2 与机器学习模块协作

清洗完成后，路由层会把清洗结果保存为：

```text
cleaned_dataset
```

机器学习模块后续会读取这个数据集执行 K-Means。因此本模块输出的数据质量会直接影响聚类结果。

### 7.3 与可视化模块协作

可视化模块可以使用清洗后的数据生成基础图表，也可以结合机器学习模块的 `analysis_result` 显示聚类结果。

### 7.4 与状态存储模块协作

上传和清洗结果会通过 `data_store.py` 写入 SQLite：

```text
raw_dataset
cleaned_dataset
metadata
```

这样系统不同接口之间可以共享数据状态。

## 8. 单元测试说明

本模块新增了以下测试文件：

```text
tests/test_file_utils.py
tests/test_clean_utils.py
tests/test_data_processing_routes.py
```

### 8.1 文件读取和导出测试

`tests/test_file_utils.py` 覆盖：

- CSV 文件读取
- GBK 中文 CSV 读取
- XLSX 文件读取
- 不支持格式拒绝
- 空文件拒绝
- 只有表头的文件拒绝
- 清洗数据导出为 CSV
- 分析结果导出为 JSON
- 缺少可导出数据时报错
- 不支持的导出类型时报错

### 8.2 数据清洗测试

`tests/test_clean_utils.py` 覆盖：

- 缺失值删除
- 重复行删除
- IQR 异常值删除
- 关闭部分规则时保留对应数据
- 字符串形式布尔值解析
- 默认规则行为
- 非 DataFrame 输入报错
- 非 JSON 对象规则报错
- 未知规则报错
- 非法布尔值报错

### 8.3 路由集成测试

`tests/test_data_processing_routes.py` 覆盖：

- `/api/upload` 可以读取 CSV 并返回 metadata
- `/api/clean` 可以调用清洗模块并返回 summary
- `/api/export?type=cleaned` 可以返回 CSV 内容

这些测试使用 mock 隔离 SQLite 状态，避免测试污染本地运行数据库。

### 8.4 测试命令

运行全部测试：

```powershell
python -m unittest discover -v
```

当前结果：

```text
Ran 33 tests
OK
```

语法编译检查：

```powershell
python -m compileall app tests
```

当前也已通过。

## 9. 验收时可以这样介绍

老师好，我负责的是项目中的数据读取、清洗和导出模块。这个模块主要负责把用户上传的 CSV 或 Excel 文件读取为 Pandas DataFrame，然后根据用户在前端选择的规则执行数据清洗，最后为后续流程提供清洗后的数据和导出结果。

在文件读取方面，我实现了 `read_uploaded_file(file)`，支持 CSV、XLS 和 XLSX 文件。CSV 读取时兼容 UTF-8、GBK 等常见编码，Excel 读取时分别使用 openpyxl 和 xlrd。读取成功后会返回 DataFrame 和文件元数据，包括文件名、格式、行数、列名和缺失值数量。

在清洗方面，我实现了 `clean_dataframe(dataframe, rules)`。目前支持删除缺失值、删除重复行和基于 IQR 方法处理异常值。模块会对清洗规则进行校验，并返回清洗摘要，例如输入行数、输出行数、删除的缺失行、重复行、异常值行数以及清洗前后的缺失值数量。

在导出方面，我实现了 `export_dataset(export_type, state)`。它可以把清洗后的数据导出为 CSV 内容，也可以把机器学习分析结果导出为 JSON 内容。这样后续用户可以获取清洗结果或分析结果。

为了保证模块可靠性，我还补充了数据处理相关测试，覆盖文件读取、数据清洗、结果导出和部分接口联动。目前全项目 33 个测试全部通过。

## 10. 答辩常见问题准备

### 问题 1：为什么读取 CSV 时要处理多种编码？

因为中文环境下 CSV 文件来源很多，有些是 UTF-8，有些是 Excel 导出的 GBK 编码。如果只支持一种编码，用户上传中文 CSV 时容易解析失败。因此我按顺序尝试 UTF-8、GBK、GB18030 等常见编码，提高兼容性。

### 问题 2：为什么清洗规则要做严格校验？

清洗规则来自前端请求，如果不校验，错误字段或非法值可能导致清洗逻辑不可预测。严格校验可以保证接口行为稳定，也方便前端根据错误信息定位问题。

### 问题 3：为什么缺失值处理是删除整行，而不是填充？

当前项目是课程实验，优先保证清洗结果简单、可解释。删除缺失值是最直接的处理方式。后续可以扩展为均值填充、中位数填充、众数填充或按字段自定义填充。

### 问题 4：为什么异常值使用 IQR 方法？

IQR 方法不依赖数据服从正态分布，适合一般表格数据的基础异常值检测。它通过四分位数判断异常范围，实现简单、解释清楚，适合作为课程项目中的第一版异常值处理方案。

### 问题 5：异常值为什么只处理数值列？

异常值检测依赖大小比较和四分位数计算，只适用于数值列。文本列没有数值意义，不能直接参与 IQR 计算。

### 问题 6：清洗结果如何给机器学习模块使用？

清洗完成后，路由会把清洗后的 DataFrame 保存为 `cleaned_dataset`。机器学习模块读取这个数据集后执行 K-Means 聚类。因此本模块相当于为后续分析提供了更干净、更稳定的数据输入。

### 问题 7：为什么导出现在返回 content，而不是直接下载文件？

项目当前接口统一返回 JSON，因此导出模块返回文件名、格式和内容；前端会基于这些内容生成下载文件，并通过页面状态提示操作结果。

### 问题 8：你怎么证明这个模块是可靠的？

我写了单元测试和接口测试。测试覆盖 CSV/Excel 读取、中文编码、缺失值、重复行、异常值处理、导出结果和错误输入等情况。目前全项目 33 个测试全部通过。

## 11. 当前不足与后续改进

当前模块已经能完成基础数据读取、清洗和导出，但仍有改进空间：

1. 缺失值处理可以增加均值、中位数、众数填充。
2. 异常值处理可以支持删除、截断、替换等多种策略。
3. 可以允许用户选择具体清洗字段，而不是对所有列统一处理。
4. 可以支持更多文件格式，例如 JSON、TSV。
5. 可以把导出接口改为真正的文件下载。
6. 可以在前端展示清洗前后对比，例如删除了多少行、哪些字段存在异常。

验收时如果老师问到不足，可以说明当前版本优先保证主流程可运行、规则清晰、结果可解释，后续可以继续扩展更细粒度的数据清洗策略。

## 12. 个人贡献总结

我在本模块中的主要贡献是把原本预留的数据处理接口，完善为可以真实读取文件、执行清洗并导出结果的数据处理模块。

具体来说，我完成了：

- CSV、XLS、XLSX 文件读取。
- CSV 多编码兼容。
- 文件元数据生成。
- 缺失值删除。
- 重复行删除。
- IQR 异常值处理。
- 清洗摘要统计。
- 清洗数据 CSV 导出。
- 分析结果 JSON 导出。
- Excel 依赖补充。
- 数据处理单元测试和路由测试。

这个模块为项目后续机器学习分析和可视化展示提供了稳定的数据基础。
