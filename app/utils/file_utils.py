"""成员B接口：文件上传、格式校验、数据读取与导出。"""

import io
import json
from pathlib import Path

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030")


def _file_extension(filename):
    return Path(filename or "").suffix.lower()


def _read_file_bytes(file):
    content = file.read()
    if not content:
        raise ValueError("文件内容为空")
    return content


def _read_csv(content):
    last_error = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error
        except pd.errors.ParserError as error:
            raise ValueError(f"CSV 文件解析失败：{error}") from error
    raise ValueError("CSV 文件编码无法识别，请使用 UTF-8 或 GBK 编码") from last_error


def _read_excel(content, extension):
    try:
        if extension == ".xlsx":
            return pd.read_excel(io.BytesIO(content), engine="openpyxl")
        return pd.read_excel(io.BytesIO(content), engine="xlrd")
    except ImportError as error:
        raise ValueError("缺少 Excel 读取依赖，请先运行 pip install -r requirements.txt") from error
    except ValueError as error:
        raise ValueError(f"Excel 文件解析失败：{error}") from error


def _normalize_columns(dataframe):
    dataframe = dataframe.copy()
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    return dataframe


def _metadata_for(dataframe, filename, extension):
    return {
        "filename": filename,
        "format": extension.lstrip(".").upper(),
        "rows": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "columns": [str(column) for column in dataframe.columns],
        "missing_values": int(dataframe.isna().sum().sum()),
    }


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _dataframe_export(dataframe, filename):
    return {
        "filename": filename,
        "format": "csv",
        "content": dataframe.to_csv(index=False),
        "rows": int(len(dataframe)),
        "columns": [str(column) for column in dataframe.columns],
    }


def read_uploaded_file(file):
    """读取上传文件。

    file 是 Flask/Werkzeug 的 FileStorage 对象，常用字段：
    - file.filename：原始文件名
    - file.stream 或 file.read()：文件内容

    期望返回：
    {
        "dataset": dataframe,
        "metadata": {"filename": "...", "rows": 0, "columns": []}
    }

    约定：
    - dataset 会被保存为 raw_dataset，并传给 clean_dataframe(dataframe, rules)
    - 不支持的格式、空文件、解析失败统一 raise ValueError("错误说明")
    - 业务代码不要直接返回 Flask response，由路由统一包装 JSON 响应
    """
    filename = file.filename or ""
    extension = _file_extension(filename)
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("仅支持 CSV、XLS 或 XLSX 文件")

    content = _read_file_bytes(file)
    if extension == ".csv":
        dataframe = _read_csv(content)
    else:
        dataframe = _read_excel(content, extension)

    dataframe = _normalize_columns(dataframe)
    if dataframe.empty or len(dataframe.columns) == 0:
        raise ValueError("文件没有可用数据")

    return {
        "dataset": dataframe,
        "metadata": _metadata_for(dataframe, filename, extension),
    }


def export_dataset(export_type, state):
    """导出清洗数据或分析结果。

    export_type: "cleaned" 或 "result"
    state: app.utils.data_store.get_export_state() 返回的数据状态

    约定：
    - 返回 dict，例如 {"filename": "...", "path": "..."} 或 {"content": "..."}
    - 不支持的导出方式或导出失败统一 raise ValueError("错误说明")
    """
    if export_type == "cleaned":
        dataframe = state.get("cleaned_dataset") if isinstance(state, dict) else None
        if dataframe is None:
            raise ValueError("没有可导出的清洗数据")
        if not hasattr(dataframe, "to_csv"):
            raise ValueError("清洗数据格式不支持 CSV 导出")
        return _dataframe_export(dataframe, "cleaned_dataset.csv")

    if export_type == "result":
        result = state.get("analysis_result") if isinstance(state, dict) else None
        if result is None:
            raise ValueError("没有可导出的分析结果")
        analysis_file = {
            "filename": "analysis_result.json",
            "format": "json",
            "content": json.dumps(result, ensure_ascii=False, indent=2, default=_json_default),
        }
        files = [analysis_file]
        prediction_result = state.get("prediction_result") if isinstance(state, dict) else None
        if prediction_result is not None:
            files.append(
                {
                    "filename": "prediction_result.json",
                    "format": "json",
                    "content": json.dumps(
                        prediction_result,
                        ensure_ascii=False,
                        indent=2,
                        default=_json_default,
                    ),
                }
            )
        return {
            **analysis_file,
            "files": files,
        }

    raise ValueError("type 仅支持 cleaned 或 result")
