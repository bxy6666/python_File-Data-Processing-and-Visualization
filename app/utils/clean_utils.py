"""成员B接口预留：缺失值、重复值、异常值等清洗逻辑。"""


def clean_dataframe(dataframe, rules):
    """按规则清洗数据。

    rules 示例：
    {"drop_missing": true, "drop_duplicates": true, "handle_outliers": false}

    期望返回：
    {
        "dataset": cleaned_dataframe,
        "summary": {"removed_rows": 0, "filled_values": 0}
    }

    约定：
    - dataframe 来自 read_uploaded_file(file) 返回的 dataset
    - 规则不合法或清洗失败统一 raise ValueError("错误说明")
    - 业务代码不要直接返回 Flask response，由路由统一包装 JSON 响应
    """
    raise NotImplementedError("数据清洗逻辑由成员B接入")
