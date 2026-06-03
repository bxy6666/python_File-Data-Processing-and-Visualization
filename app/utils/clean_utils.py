"""成员B接口：缺失值、重复值、异常值等清洗逻辑。"""


SUPPORTED_RULES = {"drop_missing", "drop_duplicates", "handle_outliers"}


def _ensure_dataframe(dataframe):
    if not hasattr(dataframe, "copy") or not hasattr(dataframe, "select_dtypes"):
        raise ValueError("清洗模块需要 Pandas DataFrame 类型数据")
    return dataframe.copy()


def _parse_bool(value, key):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError(f"{key} 必须是布尔值")


def _normalize_rules(rules):
    if rules is None:
        rules = {}
    if not isinstance(rules, dict):
        raise ValueError("清洗规则必须是 JSON 对象")

    unknown_rules = set(rules) - SUPPORTED_RULES
    if unknown_rules:
        raise ValueError(f"存在不支持的清洗规则：{', '.join(sorted(unknown_rules))}")

    return {
        key: _parse_bool(rules.get(key, False), key)
        for key in SUPPORTED_RULES
    }


def _count_missing(dataframe):
    return int(dataframe.isna().sum().sum())


def _remove_outliers_iqr(dataframe):
    numeric_columns = list(dataframe.select_dtypes(include=["number"]).columns)
    if not numeric_columns:
        return dataframe, 0, []

    outlier_mask = None
    fields = []
    for column in numeric_columns:
        series = dataframe[column].dropna()
        if series.empty:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        column_mask = (dataframe[column] < lower) | (dataframe[column] > upper)
        if column_mask.any():
            fields.append(str(column))
            outlier_mask = column_mask if outlier_mask is None else (outlier_mask | column_mask)

    if outlier_mask is None:
        return dataframe, 0, []

    removed_rows = int(outlier_mask.sum())
    return dataframe.loc[~outlier_mask].copy(), removed_rows, fields


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
    cleaned_dataframe = _ensure_dataframe(dataframe)
    normalized_rules = _normalize_rules(rules)

    input_rows = int(len(cleaned_dataframe))
    input_columns = int(len(cleaned_dataframe.columns))
    missing_before = _count_missing(cleaned_dataframe)
    duplicate_rows_before = int(cleaned_dataframe.duplicated().sum())

    removed_missing_rows = 0
    if normalized_rules["drop_missing"]:
        before_rows = len(cleaned_dataframe)
        cleaned_dataframe = cleaned_dataframe.dropna(axis=0, how="any").copy()
        removed_missing_rows = int(before_rows - len(cleaned_dataframe))

    removed_duplicate_rows = 0
    if normalized_rules["drop_duplicates"]:
        before_rows = len(cleaned_dataframe)
        cleaned_dataframe = cleaned_dataframe.drop_duplicates().copy()
        removed_duplicate_rows = int(before_rows - len(cleaned_dataframe))

    outlier_rows_removed = 0
    outlier_fields = []
    if normalized_rules["handle_outliers"]:
        cleaned_dataframe, outlier_rows_removed, outlier_fields = _remove_outliers_iqr(cleaned_dataframe)

    cleaned_dataframe = cleaned_dataframe.reset_index(drop=True)
    output_rows = int(len(cleaned_dataframe))
    missing_after = _count_missing(cleaned_dataframe)

    summary = {
        "rules": normalized_rules,
        "input_rows": input_rows,
        "input_columns": input_columns,
        "output_rows": output_rows,
        "output_columns": int(len(cleaned_dataframe.columns)),
        "missing_values_before": missing_before,
        "missing_values_after": missing_after,
        "duplicate_rows_before": duplicate_rows_before,
        "removed_missing_rows": removed_missing_rows,
        "removed_duplicate_rows": removed_duplicate_rows,
        "outlier_rows_removed": outlier_rows_removed,
        "outlier_fields": outlier_fields,
        "removed_rows": int(input_rows - output_rows),
        "filled_values": 0,
    }

    return {"dataset": cleaned_dataframe, "summary": summary}
