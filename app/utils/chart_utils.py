from flask import jsonify


SUPPORTED_CHARTS = {"bar", "line", "scatter", "box"}


def create_chart_response(chart, x_field, y_field, color_field=None):
    if chart not in SUPPORTED_CHARTS:
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "INVALID_CHART",
                    "message": "chart 仅支持 bar、line、scatter、box",
                }
            ),
            400,
        )

    return (
        jsonify(
            {
                "status": "error",
                "code": "DATA_NOT_READY",
                "owner": "成员D",
                "message": "等待上传、清洗或分析模块接入后生成图表",
                "request": {
                    "chart": chart,
                    "x": x_field,
                    "y": y_field,
                    "color": color_field or "",
                },
            }
        ),
        409,
    )
