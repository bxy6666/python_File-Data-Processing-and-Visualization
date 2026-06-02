from flask import Blueprint, jsonify, render_template, request

from .utils.chart_utils import create_chart_response

bp = Blueprint("main", __name__)


def not_implemented(owner):
    return (
        jsonify(
            {
                "status": "error",
                "code": "NOT_IMPLEMENTED",
                "owner": owner,
                "message": "该模块待对应成员接入",
            }
        ),
        501,
    )


@bp.route("/")
def index():
    return render_template("index.html")


@bp.post("/api/upload")
def upload_file():
    return not_implemented("成员A")


@bp.post("/api/clean")
def clean_data():
    return not_implemented("成员B")


@bp.post("/api/analyze")
def analyze_data():
    return not_implemented("成员C")


@bp.get("/api/visualize")
def visualize_data():
    chart = request.args.get("chart", "scatter")
    x_field = request.args.get("x", "")
    y_field = request.args.get("y", "")
    color_field = request.args.get("color", "")
    return create_chart_response(chart, x_field, y_field, color_field)


@bp.get("/api/export")
def export_data():
    return not_implemented("成员A")
