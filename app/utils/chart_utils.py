from flask import jsonify


SUPPORTED_CHARTS = {"bar", "line", "scatter", "box"}


def create_chart_response(chart):
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
                "description": "数据准备完成后，系统会自动选择适合的展示内容并生成图表说明。",
                "request": {
                    "chart": chart,
                },
            }
        ),
        409,
    )
