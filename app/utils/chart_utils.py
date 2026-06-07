"""
app/utils/chart_utils.py

成员 C — 图表可视化
对外只暴露 create_chart_response(chart, cleaned_dataset, analysis_result)。
返回 (payload_dict, http_status)，由 routes.py 通过 json_response() 统一包装，
本文件不直接操作 Flask response，也不读取 SQLite / 上传文件。

依赖：
    plotly>=5.20,<6.0   （requirements.txt 已包含）
    pandas              （成员 B 已引入）
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from .response_utils import error_payload, success_payload

# ── 支持的图表类型 ──────────────────────────────────────────────────────────────
SUPPORTED_CHARTS: frozenset[str] = frozenset({"bar", "line", "scatter", "box"})

# Plotly 默认调色板（按聚类顺序循环）
_PALETTE = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3", "#FF6692"]


# ══════════════════════════════════════════════════════════════════════════════
# 私有工具函数
# ══════════════════════════════════════════════════════════════════════════════

def _numeric_columns(df: pd.DataFrame) -> list[str]:
    """返回 DataFrame 中所有数值列的列名列表。"""
    return list(df.select_dtypes(include=["number"]).columns)


def _analysis_columns(analysis_result: dict | None) -> list[str]:
    """从 analysis_result['columns'] 中取出参与聚类的字段列表。"""
    if analysis_result and isinstance(analysis_result.get("columns"), list):
        return analysis_result["columns"]
    return []


def _label_map(analysis_result: dict | None) -> dict[int, int]:
    """
    将 analysis_result['labels'] 展开为 {row_index: cluster_id} 字典，
    供散点图、箱线图按行映射聚类颜色。

    labels 结构（来自 run_kmeans 返回）：
        [{"row_index": "0", "cluster": 1}, ...]
    """
    if not analysis_result or "labels" not in analysis_result:
        return {}
    mapping: dict[int, int] = {}
    for entry in analysis_result["labels"]:
        try:
            mapping[int(entry["row_index"])] = int(entry["cluster"])
        except (KeyError, ValueError, TypeError):
            pass
    return mapping


def _cluster_series(df: pd.DataFrame, analysis_result: dict | None) -> pd.Series | None:
    """
    根据 label_map 为 df 每一行打上聚类标签，返回 pd.Series（与 df 行数等长）。
    若无分析结果则返回 None。
    """
    lmap = _label_map(analysis_result)
    if not lmap:
        return None
    return pd.Series(
        [lmap.get(i, -1) for i in range(len(df))],
        index=df.index,
        dtype=int,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 四个图表构建函数
# ══════════════════════════════════════════════════════════════════════════════

def _build_bar_figure(
    cleaned_dataset: pd.DataFrame | None,
    analysis_result: dict | None,
) -> tuple[dict, str, list[str]]:
    """
    柱状图。
    优先：analysis_result['clusters'] 每个聚类的样本数量。
    回退：cleaned_dataset 中第一个文本/类别列的 value_counts（Top 20）。
    """
    # ── 优先：聚类数量 ────────────────────────────────────────────────────
    clusters: list[dict] = (analysis_result or {}).get("clusters") or []
    if clusters:
        x = [f"Cluster {c['cluster']}" for c in clusters]
        y = [c["count"] for c in clusters]
        fig = go.Figure(
            data=[go.Bar(x=x, y=y, name="样本数量", marker_color=_PALETTE[0])]
        )
        fig.update_layout(
            title={"text": "各聚类样本数量"},
            xaxis={"title": {"text": "聚类类别"}},
            yaxis={"title": {"text": "样本数量"}},
            margin={"l": 48, "r": 24, "t": 56, "b": 48},
        )
        return (
            fig.to_plotly_json(),
            "各 K-Means 聚类中的样本数量分布。",
            ["analysis_result.clusters.cluster", "analysis_result.clusters.count"],
        )

    # ── 回退：类别列频次 ──────────────────────────────────────────────────
    if cleaned_dataset is None or cleaned_dataset.empty:
        raise ValueError("DATA_NOT_READY")

    cat_cols = list(cleaned_dataset.select_dtypes(include=["object", "category"]).columns)
    if not cat_cols:
        raise ValueError("INVALID_CHART_DATA")

    col = cat_cols[0]
    counts = cleaned_dataset[col].value_counts().head(20)
    fig = go.Figure(
        data=[
            go.Bar(
                x=list(counts.index.astype(str)),
                y=list(counts.values),
                marker_color=_PALETTE[0],
            )
        ]
    )
    fig.update_layout(
        title={"text": f"字段「{col}」类别频次（Top 20）"},
        xaxis={"title": {"text": col}},
        yaxis={"title": {"text": "数量"}},
        margin={"l": 48, "r": 24, "t": 56, "b": 48},
    )
    return (
        fig.to_plotly_json(),
        f"字段「{col}」各类别的出现次数（Top 20）。",
        [col, "count"],
    )


def _build_line_figure(
    cleaned_dataset: pd.DataFrame | None,
    analysis_result: dict | None = None,   # 折线图不使用分析结果，保留参数供统一调用接口
) -> tuple[dict, str, list[str]]:
    """
    折线图。
    x 轴：优先找列名含 date/time/year/日期/年份/月份/时间 的列；找不到则用行序号。
    y 轴：第一个数值列。
    """
    if cleaned_dataset is None or cleaned_dataset.empty:
        raise ValueError("DATA_NOT_READY")

    num_cols = _numeric_columns(cleaned_dataset)
    if not num_cols:
        raise ValueError("INVALID_CHART_DATA")

    # 寻找时间/日期列
    time_keywords = ["date", "time", "year", "日期", "年份", "月份", "时间"]
    time_col: str | None = next(
        (c for c in cleaned_dataset.columns if any(kw in c.lower() for kw in time_keywords)),
        None,
    )

    y_col = num_cols[0]

    if time_col:
        x_vals: Any = cleaned_dataset[time_col].astype(str).tolist()
        x_label = time_col
    else:
        x_vals = list(range(len(cleaned_dataset)))
        x_label = "行序号"

    fig = go.Figure(
        data=[
            go.Scatter(
                x=x_vals,
                y=cleaned_dataset[y_col].tolist(),
                mode="lines+markers",
                name=y_col,
                line={"color": _PALETTE[1]},
                marker={"size": 5},
            )
        ]
    )
    fig.update_layout(
        title={"text": f"「{y_col}」趋势折线图"},
        xaxis={"title": {"text": x_label}},
        yaxis={"title": {"text": y_col}},
        margin={"l": 48, "r": 24, "t": 56, "b": 48},
    )
    return (
        fig.to_plotly_json(),
        f"字段「{y_col}」随「{x_label}」变化的趋势。",
        [x_label, y_col],
    )


def _build_scatter_figure(
    cleaned_dataset: pd.DataFrame | None,
    analysis_result: dict | None,
) -> tuple[dict, str, list[str]]:
    """
    散点图。
    x/y：优先取 analysis_result['columns'] 前两个；回退取 cleaned_dataset 前两个数值列；
         若只有 1 个数值列则以行序号为 x。
    颜色：若有 analysis_result['labels'] 则按聚类着色，否则统一色。
    """
    if cleaned_dataset is None or cleaned_dataset.empty:
        raise ValueError("DATA_NOT_READY")

    num_cols = _numeric_columns(cleaned_dataset)
    if not num_cols:
        raise ValueError("INVALID_CHART_DATA")

    # 确定 x/y 列
    ana_cols = [c for c in _analysis_columns(analysis_result) if c in cleaned_dataset.columns]
    if len(ana_cols) >= 2:
        x_col, y_col = ana_cols[0], ana_cols[1]
        use_index_x = False
    elif len(num_cols) >= 2:
        x_col, y_col = num_cols[0], num_cols[1]
        use_index_x = False
    else:
        x_col, y_col = "行序号", num_cols[0]
        use_index_x = True

    x_vals: Any = list(range(len(cleaned_dataset))) if use_index_x else cleaned_dataset[x_col].tolist()
    y_vals = cleaned_dataset[y_col].tolist()

    # 聚类着色
    clusters = _cluster_series(cleaned_dataset, analysis_result)

    if clusters is not None:
        unique_ids = sorted(clusters.unique())
        traces = []
        for i, cid in enumerate(unique_ids):
            mask = clusters == cid
            traces.append(
                go.Scatter(
                    x=[x_vals[j] for j, m in enumerate(mask) if m],
                    y=[y_vals[j] for j, m in enumerate(mask) if m],
                    mode="markers",
                    name=f"Cluster {cid}" if cid != -1 else "未分类",
                    marker={"color": _PALETTE[i % len(_PALETTE)], "size": 7},
                )
            )
        fields = [x_col, y_col, "cluster"]
        description = f"「{x_col}」与「{y_col}」的散点分布，颜色表示 K-Means 聚类结果。"
    else:
        traces = [
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers",
                name="数据点",
                marker={"color": _PALETTE[0], "size": 7},
            )
        ]
        fields = [x_col, y_col]
        description = f"「{x_col}」与「{y_col}」的散点分布。"

    fig = go.Figure(data=traces)
    fig.update_layout(
        title={"text": f"{x_col} vs {y_col} 散点图"},
        xaxis={"title": {"text": x_col}},
        yaxis={"title": {"text": y_col}},
        margin={"l": 48, "r": 24, "t": 56, "b": 48},
        legend={"title": {"text": "分组"}},
    )
    return fig.to_plotly_json(), description, fields


def _build_box_figure(
    cleaned_dataset: pd.DataFrame | None,
    analysis_result: dict | None,
) -> tuple[dict, str, list[str]]:
    """
    箱线图。
    有聚类标签：取第一个数值字段，按聚类分组展示分布。
    无聚类标签：展示前 1-5 个数值字段各自的分布。
    """
    if cleaned_dataset is None or cleaned_dataset.empty:
        raise ValueError("DATA_NOT_READY")

    num_cols = _numeric_columns(cleaned_dataset)
    if not num_cols:
        raise ValueError("INVALID_CHART_DATA")

    # 优先取参与聚类的数值字段，回退取前 5 个
    ana_cols = [c for c in _analysis_columns(analysis_result) if c in num_cols]
    show_cols = (ana_cols or num_cols)[:5]

    clusters = _cluster_series(cleaned_dataset, analysis_result)

    if clusters is not None:
        # 按聚类分组，只展示第一个字段（避免图过于密集）
        col = show_cols[0]
        unique_ids = sorted(clusters.unique())
        traces = [
            go.Box(
                y=cleaned_dataset.loc[clusters == cid, col].dropna().tolist(),
                name=f"Cluster {cid}" if cid != -1 else "未分类",
                marker_color=_PALETTE[i % len(_PALETTE)],
            )
            for i, cid in enumerate(unique_ids)
        ]
        fields = [col, "cluster"]
        description = f"字段「{col}」在各 K-Means 聚类中的分布，可观察离散程度与异常值。"
    else:
        traces = [
            go.Box(
                y=cleaned_dataset[col].dropna().tolist(),
                name=col,
                marker_color=_PALETTE[i % len(_PALETTE)],
            )
            for i, col in enumerate(show_cols)
        ]
        fields = show_cols
        description = f"数值字段的分布情况（共 {len(show_cols)} 个字段），展示中位数、四分位距与异常值。"

    fig = go.Figure(data=traces)
    fig.update_layout(
        title={"text": "箱线图"},
        yaxis={"title": {"text": "数值"}},
        margin={"l": 48, "r": 24, "t": 56, "b": 48},
    )
    return fig.to_plotly_json(), description, fields


# ══════════════════════════════════════════════════════════════════════════════
# 对外入口
# ══════════════════════════════════════════════════════════════════════════════

_BUILDERS = {
    "bar": _build_bar_figure,
    "line": _build_line_figure,
    "scatter": _build_scatter_figure,
    "box": _build_box_figure,
}


def create_chart_response(
    chart: str,
    cleaned_dataset: pd.DataFrame | None,
    analysis_result: dict | None,
) -> tuple[dict, int]:
    """
    图表生成入口，由 routes.py 调用。

    参数：
        chart           图表类型：bar / line / scatter / box
        cleaned_dataset 清洗后的 DataFrame（来自 get_cleaned_dataset()）
        analysis_result K-Means 分析结果 dict（来自 get_analysis_result()）

    返回：
        (payload_dict, http_status)
        payload_dict 符合项目统一响应格式，由 routes.py 通过 json_response() 包装后返回。
    """
    # ── 图表类型校验 ─────────────────────────────────────────────────────────
    if chart not in SUPPORTED_CHARTS:
        return (
            error_payload(
                "INVALID_CHART",
                f"不支持的图表类型「{chart}」，支持：bar、line、scatter、box",
                {"request": {"chart": chart}},
            ),
            400,
        )

    # ── 数据就绪检查 ─────────────────────────────────────────────────────────
    if cleaned_dataset is None and analysis_result is None:
        return (
            error_payload(
                "DATA_NOT_READY",
                "请先上传数据并完成清洗，再生成图表",
                {"request": {"chart": chart}},
            ),
            400,
        )

    # ── 图表生成 ─────────────────────────────────────────────────────────────
    try:
        figure, description, fields = _BUILDERS[chart](cleaned_dataset, analysis_result)
    except ValueError as exc:
        code = str(exc)
        if code == "DATA_NOT_READY":
            return (
                error_payload(
                    "DATA_NOT_READY",
                    "数据未准备好，请先完成上传与清洗流程",
                    {"request": {"chart": chart}},
                ),
                400,
            )
        # INVALID_CHART_DATA 或其他 ValueError
        return (
            error_payload(
                "INVALID_CHART_DATA",
                "当前数据缺少生成该图表所需的数值字段",
                {"request": {"chart": chart}},
            ),
            400,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            error_payload(
                "CHART_ERROR",
                f"图表生成时发生错误：{exc}",
                {"request": {"chart": chart}},
            ),
            500,
        )

    # ── 成功响应 ─────────────────────────────────────────────────────────────
    return (
        success_payload(
            "VISUALIZE_OK",
            "图表已创建",
            {
                "figure": figure,
                "description": description,
                "fields": fields,
            },
        ),
        200,
    )
