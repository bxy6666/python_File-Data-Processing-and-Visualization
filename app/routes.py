from flask import Blueprint, redirect, render_template, request, url_for

from .utils.chart_utils import create_chart_response
from .utils.clean_utils import clean_dataframe
from .utils.data_store import (
    activate_dataset,
    get_analysis_result,
    get_cleaned_dataset,
    get_dataset_summary,
    get_export_state,
    get_raw_dataset,
    delete_dataset_run,
    list_dataset_runs,
    set_analysis_result,
    set_cleaned_dataset,
    set_raw_dataset,
    state_summary,
)
from .utils.file_utils import export_dataset, read_uploaded_file
from .utils.ml_utils import run_kmeans
from .utils.response_utils import error_response, json_response, success_response

bp = Blueprint("main", __name__)


def not_implemented(owner, error):
    return error_response(
        "NOT_IMPLEMENTED",
        str(error),
        {"owner": owner, "state": state_summary()},
        501,
    )


def split_result(result, dataset_key="dataset"):
    if isinstance(result, dict):
        return result.get(dataset_key), result.get("metadata", {}), result.get("summary", {})
    return result, {}, {}


def parse_dataset_id():
    dataset_id = request.args.get("dataset_id")
    if not dataset_id:
        return None

    try:
        return int(dataset_id)
    except (TypeError, ValueError):
        raise ValueError("dataset_id 必须是数字")


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


@bp.get("/api/datasets")
def datasets():
    summary = state_summary()
    return success_response(
        "DATASETS_OK",
        "数据集状态已获取",
        {
            "datasets": list_dataset_runs(),
            "active_dataset": summary.get("active_dataset"),
            "state": summary,
        },
    )


@bp.post("/api/datasets/<int:dataset_id>/activate")
def activate_dataset_run(dataset_id):
    try:
        active_dataset = activate_dataset(dataset_id)
    except ValueError as error:
        return error_response("DATASET_NOT_FOUND", str(error), http_status=404)

    return success_response(
        "DATASET_ACTIVATED",
        "已切换当前处理文件",
        {"active_dataset": active_dataset, "state": state_summary()},
    )


@bp.delete("/api/datasets/<int:dataset_id>")
def delete_dataset(dataset_id):
    try:
        deleted_dataset = delete_dataset_run(dataset_id)
    except ValueError as error:
        return error_response("DATASET_NOT_FOUND", str(error), http_status=404)

    return success_response(
        "DATASET_DELETED",
        "已删除文件记录",
        {"deleted_dataset": deleted_dataset, "state": state_summary()},
    )


@bp.post("/api/upload")
def upload_file():
    file = request.files.get("file")
    if not file or not file.filename:
        return error_response("NO_FILE", "请选择要上传的 CSV 或 Excel 文件", http_status=400)

    try:
        result = read_uploaded_file(file)
    except NotImplementedError as error:
        return not_implemented("成员B", error)
    except ValueError as error:
        return error_response("INVALID_FILE", str(error), http_status=400)

    dataset, metadata, _ = split_result(result)
    if dataset is None:
        return error_response("INVALID_UPLOAD_RESULT", "上传模块未返回 dataset", http_status=500)

    dataset_id = set_raw_dataset(dataset, metadata)
    return success_response(
        "UPLOAD_OK",
        "上传成功",
        {"dataset_id": dataset_id, "file": metadata, "state": state_summary()},
    )


@bp.post("/api/clean")
def clean_data():
    dataframe = get_raw_dataset()
    if dataframe is None:
        return error_response(
            "DATA_NOT_READY",
            "请先上传数据",
            {"required": "raw_dataset", "state": state_summary()},
            409,
        )

    rules = request.get_json(silent=True) or {}
    try:
        result = clean_dataframe(dataframe, rules)
    except NotImplementedError as error:
        return not_implemented("成员B", error)
    except ValueError as error:
        return error_response("INVALID_CLEAN_RULES", str(error), http_status=400)

    cleaned_dataset, _, summary = split_result(result)
    if cleaned_dataset is None:
        return error_response("INVALID_CLEAN_RESULT", "清洗模块未返回 dataset", http_status=500)

    set_cleaned_dataset(cleaned_dataset, summary)
    return success_response(
        "CLEAN_OK",
        "清洗完成",
        {"summary": summary, "state": state_summary()},
    )


@bp.post("/api/analyze")
def analyze_data():
    payload = request.get_json(silent=True) or {}
    method = payload.get("method", "kmeans")
    if method != "kmeans":
        return error_response("INVALID_ANALYZE_METHOD", "method 仅支持 kmeans", http_status=400)

    try:
        k = int(payload.get("k", 3))
    except (TypeError, ValueError):
        return error_response("INVALID_K", "k 值必须是数字", http_status=400)

    if k < 2:
        return error_response("INVALID_K", "k 值不能小于 2", http_status=400)

    dataframe = get_cleaned_dataset()
    if dataframe is None:
        return error_response(
            "DATA_NOT_READY",
            "请先完成数据清洗",
            {"required": "cleaned_dataset", "state": state_summary()},
            409,
        )

    try:
        result = run_kmeans(dataframe, k)
    except NotImplementedError as error:
        return not_implemented("成员D", error)
    except ValueError as error:
        return error_response("INVALID_ANALYZE_PARAMS", str(error), http_status=400)

    analysis_result = result.get("result") if isinstance(result, dict) else result
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    if analysis_result is None:
        return error_response("INVALID_ANALYZE_RESULT", "分析模块未返回 result", http_status=500)

    set_analysis_result(analysis_result, summary)
    return success_response(
        "ANALYZE_OK",
        "分析完成",
        {"summary": summary, "state": state_summary()},
    )


@bp.get("/api/visualize")
def visualize_data():
    chart = request.args.get("chart", "scatter")
    payload, http_status = create_chart_response(chart, get_cleaned_dataset(), get_analysis_result())
    return json_response(payload, http_status)


@bp.get("/api/export")
def export_data():
    export_type = request.args.get("type", "result")
    if export_type not in {"cleaned", "result"}:
        return error_response("INVALID_EXPORT_TYPE", "type 仅支持 cleaned 或 result", http_status=400)

    try:
        dataset_id = parse_dataset_id()
    except ValueError as error:
        return error_response("INVALID_DATASET_ID", str(error), http_status=400)

    if dataset_id is not None and get_dataset_summary(dataset_id) is None:
        return error_response("DATASET_NOT_FOUND", "数据集不存在", http_status=404)

    required_data = (
        get_cleaned_dataset(dataset_id)
        if export_type == "cleaned"
        else get_analysis_result(dataset_id)
    )
    if required_data is None:
        return error_response(
            "DATA_NOT_READY",
            "请先完成对应的数据处理步骤",
            {"required": export_type, "state": state_summary()},
            409,
        )

    try:
        result = export_dataset(export_type, get_export_state(dataset_id))
    except NotImplementedError as error:
        return not_implemented("成员B", error)
    except ValueError as error:
        return error_response("INVALID_EXPORT", str(error), http_status=400)

    return success_response("EXPORT_OK", "导出已准备", {"export": result})
