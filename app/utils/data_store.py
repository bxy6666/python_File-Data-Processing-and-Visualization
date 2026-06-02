"""开发期单用户数据状态。

本模块只用于课程实验骨架，后续如需多用户或持久化存储，应替换为
SQLite、本地文件缓存或会话隔离的数据层。
"""

_STATE = {
    "raw_dataset": None,
    "cleaned_dataset": None,
    "analysis_result": None,
    "metadata": {},
}


def set_raw_dataset(dataset, metadata=None):
    _STATE["raw_dataset"] = dataset
    _STATE["cleaned_dataset"] = None
    _STATE["analysis_result"] = None
    _STATE["metadata"] = {"raw": metadata or {}}


def get_raw_dataset():
    return _STATE["raw_dataset"]


def set_cleaned_dataset(dataset, summary=None):
    _STATE["cleaned_dataset"] = dataset
    _STATE["analysis_result"] = None
    _STATE["metadata"]["cleaned"] = summary or {}


def get_cleaned_dataset():
    return _STATE["cleaned_dataset"]


def set_analysis_result(result, summary=None):
    _STATE["analysis_result"] = result
    _STATE["metadata"]["analysis"] = summary or {}


def get_analysis_result():
    return _STATE["analysis_result"]


def get_export_state():
    return _STATE


def state_summary():
    return {
        "has_raw_dataset": _STATE["raw_dataset"] is not None,
        "has_cleaned_dataset": _STATE["cleaned_dataset"] is not None,
        "has_analysis_result": _STATE["analysis_result"] is not None,
        "metadata": _STATE["metadata"],
    }
