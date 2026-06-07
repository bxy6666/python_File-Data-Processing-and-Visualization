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

# 图表调色板（按聚类顺序循环），保持课程演示页清晰、克制。
_PALETTE = ["#4F46E5", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#64748B"]
_FONT_FAMILY = "Inter, Microsoft YaHei, PingFang SC, Arial, sans-serif"


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


def _label_map(analysis_result: dict | None) -> dict[str, int]:
    """
    将 analysis_result['labels'] 展开为 {row_index: cluster_id} 字典，
    供散点图、箱线图按行映射聚类颜色。

    labels 结构（来自 run_kmeans 返回）：
        [{"row_index": "0", "cluster": 1}, ...]
    """
    if not analysis_result or "labels" not in analysis_result:
        return {}
    mapping: dict[str, int] = {}
    for entry in analysis_result["labels"]:
        try:
            mapping[str(entry["row_index"])] = int(entry["cluster"])
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
    return pd.Series([lmap.get(str(index), -1) for index in df.index], index=df.index, dtype=int)


def _figure_json(fig: go.Figure) -> dict:
    """转成前端 Plotly.js 可直接消费的轻量 JSON。"""
    figure = fig.to_plotly_json()
    # Plotly Python 默认会展开 template，前端已有 Plotly.js，不需要传这块大对象。
    if isinstance(figure.get("layout"), dict):
        figure["layout"].pop("template", None)
    return figure


def _apply_common_layout(
    fig: go.Figure,
    title: str,
    x_title: str | None = None,
    y_title: str | None = None,
    *,
    legend_title: str | None = None,
    height: int = 520,
) -> go.Figure:
    """统一四类图的版式，使图表落在画布中央且细节更易读。"""
    fig.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 18}},
        autosize=True,
        height=height,
        font={"family": _FONT_FAMILY, "size": 12, "color": "#111827"},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        colorway=_PALETTE,
        margin={"l": 64, "r": 32, "t": 72, "b": 64},
        hoverlabel={
            "bgcolor": "#111827",
            "bordercolor": "#111827",
            "font": {"color": "#ffffff", "family": _FONT_FAMILY, "size": 12},
        },
    )
    fig.update_xaxes(
        title={"text": x_title} if x_title else None,
        showgrid=True,
        gridcolor="#eef2f7",
        linecolor="#d9e1ec",
        zeroline=False,
        automargin=True,
    )
    fig.update_yaxes(
        title={"text": y_title} if y_title else None,
        showgrid=True,
        gridcolor="#eef2f7",
        linecolor="#d9e1ec",
        zeroline=False,
        automargin=True,
    )
    if legend_title:
        fig.update_layout(
            legend={
                "title": {"text": legend_title},
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            }
        )
    return fig


def _time_column(df: pd.DataFrame) -> str | None:
    """按列名寻找适合作为趋势图 x 轴的时间字段。"""
    preferred_keywords = ["year", "年份", "release_year", "date", "日期", "time", "时间", "月份", "month"]
    for keyword in preferred_keywords:
        for column in df.columns:
            if keyword in str(column).lower():
                return column
    return None


def _format_tick_text(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 26 else f"{text[:23]}..."


def _spread_numeric_values(values: list[Any], ratio: float = 0.006) -> list[Any]:
    """对数值散点做轻微、可重复的显示错位，减少点重叠。"""
    numeric_values = [float(value) for value in values if pd.notna(value)]
    if len(numeric_values) < 2:
        return values

    value_range = max(numeric_values) - min(numeric_values)
    if value_range == 0:
        value_range = max(abs(numeric_values[0]), 1.0)

    step = value_range * ratio
    offsets = (-2, -1, 0, 1, 2)
    spread_values = []
    for index, value in enumerate(values):
        if pd.isna(value):
            spread_values.append(value)
            continue
        spread_values.append(float(value) + offsets[index % len(offsets)] * step)
    return spread_values


def _is_numeric_values(values: list[Any]) -> bool:
    try:
        pd.to_numeric(pd.Series(values).dropna())
    except (TypeError, ValueError):
        return False
    return True


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
        x = [f"Cluster {c.get('cluster')}" for c in clusters]
        y = [int(c.get("count", 0)) for c in clusters]
        center_text = []
        for cluster in clusters:
            center = cluster.get("center") if isinstance(cluster, dict) else {}
            if isinstance(center, dict) and center:
                top_fields = list(center.items())[:3]
                center_text.append("<br>".join(f"{key}: {value}" for key, value in top_fields))
            else:
                center_text.append("无中心点信息")

        fig = go.Figure(
            data=[
                go.Bar(
                    x=x,
                    y=y,
                    name="样本数量",
                    marker={"color": _PALETTE[: len(x)], "line": {"color": "#ffffff", "width": 1}},
                    customdata=center_text,
                    hovertemplate="<b>%{x}</b><br>样本数量：%{y}<br>%{customdata}<extra></extra>",
                )
            ]
        )
        _apply_common_layout(fig, "各聚类样本数量", "聚类类别", "样本数量")
        return (
            _figure_json(fig),
            "各 K-Means 聚类中的样本数量分布；悬停可查看每类中心点的主要字段。",
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
    labels = [_format_tick_text(value) for value in counts.index.astype(str)]
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=list(counts.values),
                marker={"color": _PALETTE[0], "line": {"color": "#ffffff", "width": 1}},
                customdata=list(counts.index.astype(str)),
                hovertemplate="<b>%{customdata}</b><br>数量：%{y}<extra></extra>",
            )
        ]
    )
    _apply_common_layout(fig, f"字段「{col}」类别频次（Top 20）", col, "数量")
    return (
        _figure_json(fig),
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
    time_col = _time_column(cleaned_dataset)

    y_col = num_cols[0]

    if time_col:
        raw_x = cleaned_dataset[time_col]
        x_label = time_col
    else:
        raw_x = pd.Series(range(len(cleaned_dataset)), index=cleaned_dataset.index)
        x_label = "行序号"

    plot_frame = pd.DataFrame({"x": raw_x, "y": cleaned_dataset[y_col]}).dropna()
    if time_col and not pd.api.types.is_numeric_dtype(plot_frame["x"]):
        parsed_x = pd.to_datetime(plot_frame["x"], errors="coerce")
        if parsed_x.notna().sum() >= max(2, len(plot_frame) // 2):
            plot_frame = plot_frame.assign(x=parsed_x).dropna()
    plot_frame = plot_frame.groupby("x", as_index=False)["y"].mean().sort_values("x")
    x_vals: Any = [value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else value for value in plot_frame["x"]]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=x_vals,
                y=plot_frame["y"].tolist(),
                mode="lines+markers",
                name=y_col,
                line={"color": _PALETTE[0], "width": 2.5},
                marker={"size": 6, "color": _PALETTE[0], "line": {"color": "#ffffff", "width": 1}},
                hovertemplate=f"{x_label}：%{{x}}<br>{y_col}：%{{y:,.2f}}<extra></extra>",
            )
        ]
    )
    _apply_common_layout(fig, f"「{y_col}」趋势折线图", x_label, y_col)
    return (
        _figure_json(fig),
        f"字段「{y_col}」随「{x_label}」变化的趋势；相同横轴值会自动取平均值。",
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

    if use_index_x:
        plot_frame = pd.DataFrame({"x": range(len(cleaned_dataset)), "y": cleaned_dataset[y_col]}, index=cleaned_dataset.index)
    else:
        plot_frame = cleaned_dataset[[x_col, y_col]].rename(columns={x_col: "x", y_col: "y"})
    plot_frame = plot_frame.dropna()
    x_vals: Any = plot_frame["x"].tolist()
    y_vals = plot_frame["y"].tolist()
    original_x_vals = list(x_vals)
    original_y_vals = list(y_vals)
    if _is_numeric_values(x_vals):
        x_vals = _spread_numeric_values(x_vals)
    if _is_numeric_values(y_vals):
        y_vals = _spread_numeric_values(y_vals)

    # 聚类着色
    clusters = _cluster_series(plot_frame, analysis_result)

    if clusters is not None:
        unique_ids = sorted(clusters.unique())
        traces = []
        for i, cid in enumerate(unique_ids):
            mask = (clusters == cid).tolist()
            traces.append(
                go.Scatter(
                    x=[x_vals[j] for j, m in enumerate(mask) if m],
                    y=[y_vals[j] for j, m in enumerate(mask) if m],
                    customdata=[
                        [original_x_vals[j], original_y_vals[j]]
                        for j, m in enumerate(mask)
                        if m
                    ],
                    mode="markers",
                    name=f"Cluster {cid}" if cid != -1 else "未分类",
                    marker={
                        "color": _PALETTE[i % len(_PALETTE)],
                        "size": 2,
                        "opacity": 0.72,
                        "line": {"color": "#ffffff", "width": 0.25},
                    },
                    hovertemplate=f"{x_col}：%{{customdata[0]:,.2f}}<br>{y_col}：%{{customdata[1]:,.2f}}<br>分组：%{{fullData.name}}<extra></extra>",
                )
            )
        fields = [x_col, y_col, "cluster"]
        description = f"「{x_col}」与「{y_col}」的散点分布，颜色表示 K-Means 聚类结果。"
    else:
        traces = [
            go.Scatter(
                x=x_vals,
                y=y_vals,
                customdata=[[x, y] for x, y in zip(original_x_vals, original_y_vals)],
                mode="markers",
                name="数据点",
                marker={"color": _PALETTE[0], "size": 2, "opacity": 0.72, "line": {"color": "#ffffff", "width": 0.25}},
                hovertemplate=f"{x_col}：%{{customdata[0]:,.2f}}<br>{y_col}：%{{customdata[1]:,.2f}}<extra></extra>",
            )
        ]
        fields = [x_col, y_col]
        description = f"「{x_col}」与「{y_col}」的散点分布。"

    fig = go.Figure(data=traces)
    _apply_common_layout(fig, f"{x_col} vs {y_col} 散点图", x_col, y_col, legend_title="分组")
    fig.update_xaxes(tickformat=".2~s")
    fig.update_yaxes(tickformat=".2~s")
    return _figure_json(fig), description, fields


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
                boxmean=True,
                jitter=0.28,
                pointpos=-1.4,
                boxpoints="outliers",
                hovertemplate="%{fullData.name}<br>数值：%{y:,.2f}<extra></extra>",
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
                boxmean=True,
                jitter=0.28,
                pointpos=-1.4,
                boxpoints="outliers",
                hovertemplate="%{fullData.name}<br>数值：%{y:,.2f}<extra></extra>",
            )
            for i, col in enumerate(show_cols)
        ]
        fields = show_cols
        description = f"数值字段的分布情况（共 {len(show_cols)} 个字段），展示中位数、四分位距与异常值。"

    fig = go.Figure(data=traces)
    _apply_common_layout(fig, "箱线图", None, "数值", legend_title="分组")
    return _figure_json(fig), description, fields


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
