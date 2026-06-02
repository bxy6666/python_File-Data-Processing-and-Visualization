"""成员C接口预留：图表生成、Plotly figure 与图表说明。"""

from .response_utils import error_payload


SUPPORTED_CHARTS = {"bar", "line", "scatter", "box"}


def create_chart_response(chart, cleaned_dataset=None, analysis_result=None):
    """生成图表响应。

    期望返回：
    (
        {
            "status": "success",
            "code": "VISUALIZE_OK",
            "message": "图表已创建",
            "data": {
                "figure": {"data": [], "layout": {}},
                "description": "图表说明",
                "fields": []
            }
        },
        200
    )

    约定：
    - chart 只来自前端图表类型选择，不再接收 x/y/color 字段
    - cleaned_dataset 来自 clean_dataframe(dataframe, rules) 返回的 dataset
    - analysis_result 来自 run_kmeans(dataframe, k) 返回的 result
    - figure 必须是 Plotly.js 可直接渲染的结构
    - 业务代码不要直接返回 Flask response，由路由统一包装 JSON 响应
    """
    if chart not in SUPPORTED_CHARTS:
        return (
            error_payload(
                "INVALID_CHART",
                "chart 仅支持 bar、line、scatter、box",
                {"supported_charts": sorted(SUPPORTED_CHARTS)},
            ),
            400,
        )

    request_data = {"request": {"chart": chart}}
    if cleaned_dataset is None and analysis_result is None:
        return (
            error_payload(
                "DATA_NOT_READY",
                "请先完成上传、清洗或分析后再生成图表",
                {
                    **request_data,
                    "description": "数据准备完成后，系统会自动选择适合的展示内容并生成图表说明。",
                },
            ),
            409,
        )

    return (
        error_payload(
            "NOT_IMPLEMENTED",
            "图表生成逻辑由成员C接入",
            {
                **request_data,
                "description": "数据准备完成后，系统会自动选择适合的展示内容并生成图表说明。",
            },
        ),
        501,
    )
