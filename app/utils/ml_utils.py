"""成员D接口：K-Means 聚类与分析结果生成。"""

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
