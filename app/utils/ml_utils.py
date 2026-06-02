"""成员D接口预留：K-Means聚类与分析结果生成。"""


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
    raise NotImplementedError("机器学习分析逻辑由成员D接入")
