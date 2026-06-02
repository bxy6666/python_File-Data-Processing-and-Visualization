from flask import Blueprint, jsonify, redirect, render_template, request, url_for

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
    return redirect(url_for("main.dashboard"))


@bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", active_page="dashboard")


@bp.route("/documents")
def documents():
    return render_template("documents.html", active_page="documents")


@bp.route("/workflow")
def workflow():
    return render_template("workflow.html", active_page="workflow")


@bp.route("/visualization")
def visualization():
    return render_template("visualization.html", active_page="visualization")


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
    return create_chart_response(chart)


@bp.get("/api/export")
def export_data():
    return not_implemented("成员A")
