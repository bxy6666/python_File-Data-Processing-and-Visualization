"""成员D接口：K-Means 聚类与分析结果生成。"""

import math
import os


def _load_sklearn():
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError as error:
        raise ValueError("缺少 scikit-learn 依赖，请先运行 pip install -r requirements.txt") from error

    return KMeans, StandardScaler


def _round_float(value):
    return round(float(value), 6)


def _select_numeric_dataframe(dataframe):
    if not hasattr(dataframe, "select_dtypes"):
        raise ValueError("K-Means 需要 Pandas DataFrame 类型数据")

    numeric_dataframe = dataframe.select_dtypes(include=["number"]).copy()
    if numeric_dataframe.empty or len(numeric_dataframe.columns) == 0:
        raise ValueError("数据中没有可用于聚类的数值列")

    before_rows = len(numeric_dataframe)
    numeric_dataframe = numeric_dataframe.dropna(axis=0, how="any")
    if numeric_dataframe.empty:
        raise ValueError("数值列中没有可用于聚类的有效样本")

    return numeric_dataframe.astype(float), before_rows - len(numeric_dataframe)


def _to_dataframe(input_data):
    if hasattr(input_data, "select_dtypes"):
        return input_data

    try:
        import pandas as pd
    except ImportError as error:
        raise ValueError("预测输入需要 Pandas DataFrame 或可转换为 DataFrame 的数据") from error

    if isinstance(input_data, dict):
        return pd.DataFrame([input_data])
    if isinstance(input_data, list):
        return pd.DataFrame(input_data)

    raise ValueError("预测输入格式不支持，请传入 DataFrame 或 JSON 数组")


def _validate_predict_model(analysis_result):
    if not isinstance(analysis_result, dict):
        raise ValueError("分析结果格式无效")

    model = analysis_result.get("model")
    if not isinstance(model, dict):
        raise ValueError("当前分析结果不包含可用于预测的模型参数，请重新执行分析")

    columns = model.get("columns")
    scaler = model.get("scaler")
    centers_scaled = model.get("centers_scaled")
    k = model.get("k")

    if not isinstance(columns, list) or not columns:
        raise ValueError("模型字段信息无效")
    if not isinstance(scaler, dict):
        raise ValueError("模型标准化参数无效")
    if not isinstance(centers_scaled, list) or not centers_scaled:
        raise ValueError("模型聚类中心参数无效")

    mean = scaler.get("mean")
    scale = scaler.get("scale")
    if not isinstance(mean, list) or not isinstance(scale, list):
        raise ValueError("模型标准化参数无效")

    if len(columns) != len(mean) or len(columns) != len(scale):
        raise ValueError("模型字段与标准化参数不一致")

    for center in centers_scaled:
        if not isinstance(center, list) or len(center) != len(columns):
            raise ValueError("模型聚类中心维度无效")

    return {
        "k": int(k if k is not None else len(centers_scaled)),
        "columns": columns,
        "mean": [float(value) for value in mean],
        "scale": [float(value) for value in scale],
        "centers_scaled": [[float(value) for value in center] for center in centers_scaled],
    }


def run_kmeans(dataframe, k):
    """执行 K-Means 聚类。

    dataframe: 优先使用清洗后的数据
    k: 聚类数量

    期望返回：
    {
        "result": analysis_result,
        "summary": {"k": 3, "columns": [], "clusters": []}
    }

    约定：
    - dataframe 来自 clean_dataframe(dataframe, rules) 返回的 dataset
    - 参数不合法或分析失败统一 raise ValueError("错误说明")
    - 业务代码不要直接返回 Flask response，由路由统一包装 JSON 响应
    """
    KMeans, StandardScaler = _load_sklearn()

    try:
        k = int(k)
    except (TypeError, ValueError) as error:
        raise ValueError("k 值必须是数字") from error

    if k < 2:
        raise ValueError("k 值不能小于 2")

    numeric_dataframe, skipped_rows = _select_numeric_dataframe(dataframe)
    row_count = len(numeric_dataframe)
    if k > row_count:
        raise ValueError(f"k 值不能大于可用样本数 {row_count}")

    columns = list(numeric_dataframe.columns)
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(numeric_dataframe)

    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = model.fit_predict(scaled_features)
    centers = scaler.inverse_transform(model.cluster_centers_)

    clusters = []
    for cluster_id in range(k):
        center = {
            column: _round_float(centers[cluster_id][column_index])
            for column_index, column in enumerate(columns)
        }
        clusters.append(
            {
                "cluster": cluster_id,
                "count": int((labels == cluster_id).sum()),
                "center": center,
            }
        )

    row_labels = [
        {"row_index": str(index), "cluster": int(cluster)}
        for index, cluster in zip(numeric_dataframe.index, labels)
    ]

    result = {
        "method": "kmeans",
        "k": k,
        "columns": columns,
        "rows_used": row_count,
        "rows_skipped": skipped_rows,
        "inertia": _round_float(model.inertia_),
        "clusters": clusters,
        "labels": row_labels,
        "model": {
            "type": "kmeans",
            "k": k,
            "columns": columns,
            "scaler": {
                "mean": [_round_float(value) for value in scaler.mean_],
                "scale": [_round_float(value) for value in scaler.scale_],
            },
            "centers_scaled": [
                [_round_float(value) for value in center]
                for center in model.cluster_centers_.tolist()
            ],
        },
    }

    summary = {
        "k": k,
        "columns": columns,
        "rows_used": row_count,
        "rows_skipped": skipped_rows,
        "inertia": result["inertia"],
        "clusters": clusters,
    }

    return {"result": result, "summary": summary}


def run_kmeans_predict(input_data, analysis_result):
    """使用历史 K-Means 结果对新样本进行簇预测。"""
    model = _validate_predict_model(analysis_result)
    dataframe = _to_dataframe(input_data)

    missing_columns = [column for column in model["columns"] if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(f"预测数据缺少字段: {', '.join(missing_columns)}")

    selected_dataframe = dataframe[model["columns"]].copy()
    rows_received = len(selected_dataframe)
    selected_dataframe = selected_dataframe.dropna(axis=0, how="any")
    if selected_dataframe.empty:
        raise ValueError("预测数据中没有可用样本")

    try:
        selected_dataframe = selected_dataframe.astype(float)
    except (TypeError, ValueError) as error:
        raise ValueError("预测字段必须都是数值类型") from error

    predictions = []
    cluster_counts = {cluster_id: 0 for cluster_id in range(model["k"])}

    for row_index, row in selected_dataframe.iterrows():
        scaled_row = []
        for idx, value in enumerate(row.tolist()):
            denominator = model["scale"][idx]
            if denominator == 0:
                scaled_row.append(value - model["mean"][idx])
            else:
                scaled_row.append((value - model["mean"][idx]) / denominator)

        best_cluster = 0
        best_distance = None
        for cluster_id, center in enumerate(model["centers_scaled"]):
            distance = sum((scaled_row[col_idx] - center[col_idx]) ** 2 for col_idx in range(len(center)))
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_cluster = cluster_id

        cluster_counts[best_cluster] = cluster_counts.get(best_cluster, 0) + 1
        predictions.append(
            {
                "row_index": str(row_index),
                "cluster": int(best_cluster),
                "distance": _round_float(math.sqrt(best_distance if best_distance is not None else 0.0)),
            }
        )

    cluster_summary = [
        {"cluster": cluster_id, "count": int(cluster_counts.get(cluster_id, 0))}
        for cluster_id in range(model["k"])
    ]

    result = {
        "method": "kmeans_predict",
        "k": model["k"],
        "columns": model["columns"],
        "rows_received": int(rows_received),
        "rows_used": int(len(selected_dataframe)),
        "rows_skipped": int(rows_received - len(selected_dataframe)),
        "predictions": predictions,
        "clusters": cluster_summary,
    }

    summary = {
        "k": model["k"],
        "columns": model["columns"],
        "rows_received": result["rows_received"],
        "rows_used": result["rows_used"],
        "rows_skipped": result["rows_skipped"],
        "clusters": cluster_summary,
    }

    return {"result": result, "summary": summary}
