"""成员B接口预留：文件上传、格式校验、数据读取与导出。"""


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
    raise NotImplementedError("文件读取逻辑由成员B接入")


def export_dataset(export_type, state):
    """导出清洗数据或分析结果。

    export_type: "cleaned" 或 "result"
    state: app.utils.data_store.get_export_state() 返回的数据状态

    约定：
    - 返回 dict，例如 {"filename": "...", "path": "..."} 或 {"content": "..."}
    - 不支持的导出方式或导出失败统一 raise ValueError("错误说明")
    """
    raise NotImplementedError("数据导出逻辑由成员B接入")
