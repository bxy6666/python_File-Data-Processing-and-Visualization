"""SQLite 数据状态存储。

本模块负责保存上传、清洗、分析流程中的中间数据。为保持成员接口简单，
dataset、analysis_result 等 Python 对象会通过 pickle 存入 SQLite。
该方案适合本课程实验的本地可信环境；若后续需要多用户或线上部署，
应改为按用户隔离的数据表或文件存储方案。
"""

import pickle
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd


DATABASE_PATH = Path(__file__).resolve().parents[2] / "instance" / "dataflow.sqlite3"
DATABASE_LABEL = "instance/dataflow.sqlite3"


def connect_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS data_state (
            key TEXT PRIMARY KEY,
            value BLOB NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS dataset_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            metadata BLOB NOT NULL,
            raw_dataset BLOB NOT NULL,
            cleaned_dataset BLOB,
            analysis_result BLOB,
            clean_summary BLOB,
            analysis_summary BLOB,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(dataset_runs)").fetchall()}
    if "prediction_result" not in columns:
        connection.execute("ALTER TABLE dataset_runs ADD COLUMN prediction_result BLOB")
    clear_pickled_nulls(connection)
    return connection


@contextmanager
def database_connection():
    connection = connect_database()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def serialize(value):
    return sqlite3.Binary(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))


def deserialize(value):
    if value is None:
        return None
    return pickle.loads(value)


def serialize_nullable(value):
    if value is None:
        return None
    return serialize(value)


def clear_pickled_nulls(connection):
    nullable_fields = ("cleaned_dataset", "analysis_result", "prediction_result")
    for field in nullable_fields:
        rows = connection.execute(
            f"SELECT id, {field} FROM dataset_runs WHERE {field} IS NOT NULL"
        ).fetchall()
        for dataset_id, stored_value in rows:
            try:
                value = deserialize(stored_value)
            except (pickle.UnpicklingError, TypeError, EOFError):
                continue
            if value is None:
                connection.execute(
                    f"UPDATE dataset_runs SET {field} = NULL WHERE id = ?",
                    (dataset_id,),
                )


def upsert_value(connection, key, value):
    connection.execute(
        """
        INSERT INTO data_state (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """,
        (key, serialize(value)),
    )


def get_value(key, default=None):
    with database_connection() as connection:
        row = connection.execute("SELECT value FROM data_state WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return deserialize(row[0])


def set_active_dataset_id(connection, dataset_id):
    upsert_value(connection, "active_dataset_id", int(dataset_id))


def get_active_dataset_id():
    active_id = get_value("active_dataset_id")
    if active_id is not None:
        return int(active_id)

    with database_connection() as connection:
        row = connection.execute(
            "SELECT id FROM dataset_runs ORDER BY updated_at DESC, id DESC LIMIT 1"
        ).fetchone()

    return int(row[0]) if row else None


def clear_active_dataset_id(connection):
    connection.execute("DELETE FROM data_state WHERE key = ?", ("active_dataset_id",))


def _dataset_row_to_dict(row):
    if row is None:
        return None

    return {
        "id": int(row[0]),
        "filename": row[1],
        "metadata": deserialize(row[2]) or {},
        "raw_dataset": deserialize(row[3]),
        "cleaned_dataset": deserialize(row[4]),
        "analysis_result": deserialize(row[5]),
        "prediction_result": deserialize(row[6]),
        "clean_summary": deserialize(row[7]) or {},
        "analysis_summary": deserialize(row[8]) or {},
        "created_at": row[9],
        "updated_at": row[10],
    }


def _summary_row_to_dict(row, active_dataset_id=None):
    if row is None:
        return None

    dataset_id = int(row[0])
    return {
        "id": dataset_id,
        "filename": row[1],
        "metadata": deserialize(row[2]) or {},
        "clean_summary": deserialize(row[7]) or {},
        "analysis_summary": deserialize(row[8]) or {},
        "created_at": row[9],
        "updated_at": row[10],
        "is_active": active_dataset_id == dataset_id,
        "status": {
            "has_raw_dataset": bool(row[3]),
            "has_cleaned_dataset": bool(row[4]),
            "has_analysis_result": bool(row[5]),
            "has_prediction_result": bool(row[6]),
        },
    }


def _fetch_dataset(connection, dataset_id):
    row = connection.execute(
        """
        SELECT id, filename, metadata, raw_dataset, cleaned_dataset, analysis_result,
               prediction_result,
               clean_summary, analysis_summary, created_at, updated_at
        FROM dataset_runs
        WHERE id = ?
        """,
        (int(dataset_id),),
    ).fetchone()
    return _dataset_row_to_dict(row)


def _fetch_dataset_summary(connection, dataset_id, active_dataset_id=None):
    row = connection.execute(
        """
        SELECT id, filename, metadata,
               raw_dataset IS NOT NULL,
               cleaned_dataset IS NOT NULL,
               analysis_result IS NOT NULL,
               prediction_result IS NOT NULL,
               clean_summary, analysis_summary, created_at, updated_at
        FROM dataset_runs
        WHERE id = ?
        """,
        (int(dataset_id),),
    ).fetchone()
    return _summary_row_to_dict(row, active_dataset_id)


def _fetch_all_dataset_summaries(connection, active_dataset_id=None):
    rows = connection.execute(
        """
        SELECT id, filename, metadata,
               raw_dataset IS NOT NULL,
               cleaned_dataset IS NOT NULL,
               analysis_result IS NOT NULL,
               prediction_result IS NOT NULL,
               clean_summary, analysis_summary, created_at, updated_at
        FROM dataset_runs
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    return [_summary_row_to_dict(row, active_dataset_id) for row in rows]


def create_dataset_run(dataset, metadata=None):
    metadata = metadata or {}
    filename = metadata.get("filename") or "uploaded_dataset"

    with database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO dataset_runs (filename, metadata, raw_dataset)
            VALUES (?, ?, ?)
            """,
            (filename, serialize(metadata), serialize(dataset)),
        )
        dataset_id = int(cursor.lastrowid)
        set_active_dataset_id(connection, dataset_id)

    return dataset_id


def list_dataset_runs():
    active_dataset_id = get_active_dataset_id()
    with database_connection() as connection:
        return _fetch_all_dataset_summaries(connection, active_dataset_id)


def get_dataset_summary(dataset_id):
    active_dataset_id = get_active_dataset_id()
    with database_connection() as connection:
        return _fetch_dataset_summary(connection, dataset_id, active_dataset_id)


def get_active_dataset_summary():
    active_dataset_id = get_active_dataset_id()
    if active_dataset_id is None:
        return None
    return get_dataset_summary(active_dataset_id)


def activate_dataset(dataset_id):
    with database_connection() as connection:
        dataset = _fetch_dataset_summary(connection, dataset_id, int(dataset_id))
        if dataset is None:
            raise ValueError("数据集不存在")
        set_active_dataset_id(connection, dataset_id)

    return get_dataset_summary(dataset_id)


def delete_dataset_run(dataset_id):
    dataset_id = int(dataset_id)
    with database_connection() as connection:
        dataset = _fetch_dataset_summary(connection, dataset_id, get_active_dataset_id())
        if dataset is None:
            raise ValueError("数据集不存在")

        connection.execute("DELETE FROM dataset_runs WHERE id = ?", (dataset_id,))
        if dataset.get("is_active"):
            row = connection.execute(
                "SELECT id FROM dataset_runs ORDER BY updated_at DESC, id DESC LIMIT 1"
            ).fetchone()
            if row:
                set_active_dataset_id(connection, int(row[0]))
            else:
                clear_active_dataset_id(connection)

    return dataset


def _resolve_dataset_id(dataset_id=None):
    if dataset_id is not None:
        return int(dataset_id)
    return get_active_dataset_id()


def _get_dataset_value(field, dataset_id=None):
    resolved_id = _resolve_dataset_id(dataset_id)
    if resolved_id is None:
        return None

    with database_connection() as connection:
        dataset = _fetch_dataset(connection, resolved_id)

    if dataset is None:
        return None
    return dataset.get(field)


def _update_active_dataset(**fields):
    dataset_id = get_active_dataset_id()
    if dataset_id is None:
        raise ValueError("请先上传数据")

    allowed_fields = {
        "cleaned_dataset",
        "analysis_result",
        "prediction_result",
        "clean_summary",
        "analysis_summary",
    }
    unknown_fields = set(fields) - allowed_fields
    if unknown_fields:
        raise ValueError(f"不支持更新字段：{', '.join(sorted(unknown_fields))}")

    assignments = [f"{field} = ?" for field in fields]
    values = [serialize_nullable(value) for value in fields.values()]
    assignments.append("updated_at = CURRENT_TIMESTAMP")

    with database_connection() as connection:
        connection.execute(
            f"UPDATE dataset_runs SET {', '.join(assignments)} WHERE id = ?",
            (*values, dataset_id),
        )


def get_metadata():
    active_summary = get_active_dataset_summary()
    if active_summary is None:
        return {}
    return {
        "raw": active_summary.get("metadata", {}),
        "cleaned": active_summary.get("clean_summary", {}),
        "analysis": active_summary.get("analysis_summary", {}),
    }


def set_raw_dataset(dataset, metadata=None):
    dataset_id = create_dataset_run(dataset, metadata)
    return dataset_id


def get_raw_dataset(dataset_id=None):
    return _get_dataset_value("raw_dataset", dataset_id)


def set_cleaned_dataset(dataset, summary=None):
    _update_active_dataset(
        cleaned_dataset=dataset,
        clean_summary=summary or {},
        analysis_result=None,
        prediction_result=None,
        analysis_summary={},
    )


def get_cleaned_dataset(dataset_id=None):
    return _get_dataset_value("cleaned_dataset", dataset_id)


def set_analysis_result(result, summary=None):
    _update_active_dataset(analysis_result=result, analysis_summary=summary or {}, prediction_result=None)


def get_analysis_result(dataset_id=None):
    return _get_dataset_value("analysis_result", dataset_id)


def set_prediction_result(result):
    _update_active_dataset(prediction_result=result)


def get_prediction_result(dataset_id=None):
    return _get_dataset_value("prediction_result", dataset_id)


def _json_safe_value(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        value = value.item()

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def get_dataset_preview(dataset_id=None, dataset_type="raw", limit=10):
    if dataset_type not in {"raw", "cleaned"}:
        raise ValueError("type 仅支持 raw 或 cleaned")

    try:
        preview_limit = int(limit)
    except (TypeError, ValueError) as error:
        raise ValueError("limit 必须是数字") from error

    if preview_limit < 1:
        raise ValueError("limit 不能小于 1")
    preview_limit = min(preview_limit, 50)

    dataframe = get_raw_dataset(dataset_id) if dataset_type == "raw" else get_cleaned_dataset(dataset_id)
    if dataframe is None:
        return None

    columns = [str(column) for column in dataframe.columns]
    rows = []
    for row_values in dataframe.head(preview_limit).itertuples(index=False, name=None):
        rows.append(
            {
                column: _json_safe_value(row_values[index])
                for index, column in enumerate(columns)
            }
        )

    return {
        "dataset_id": _resolve_dataset_id(dataset_id),
        "type": dataset_type,
        "limit": preview_limit,
        "columns": columns,
        "rows": rows,
        "total_rows": int(len(dataframe)),
        "total_columns": int(len(dataframe.columns)),
    }


def get_predict_input_rows(dataset_id=None):
    dataframe = get_cleaned_dataset(dataset_id)
    analysis_result = get_analysis_result(dataset_id)
    if dataframe is None or analysis_result is None:
        return None

    model = analysis_result.get("model") if isinstance(analysis_result, dict) else {}
    columns = model.get("columns") or analysis_result.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ValueError("当前分析结果缺少可预测字段")

    missing_columns = [column for column in columns if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(f"清洗后数据缺少字段: {', '.join(missing_columns)}")

    selected_dataframe = dataframe[columns].copy()
    rows_received = len(selected_dataframe)
    selected_dataframe = selected_dataframe.dropna(axis=0, how="any")

    try:
        selected_dataframe = selected_dataframe.astype(float)
    except (TypeError, ValueError) as error:
        raise ValueError("预测字段必须都是数值类型") from error

    rows = []
    for row_values in selected_dataframe.itertuples(index=False, name=None):
        rows.append(
            {
                column: _json_safe_value(row_values[index])
                for index, column in enumerate(columns)
            }
        )

    return {
        "dataset_id": _resolve_dataset_id(dataset_id),
        "columns": columns,
        "rows": rows,
        "rows_received": int(rows_received),
        "rows_used": int(len(selected_dataframe)),
        "rows_skipped": int(rows_received - len(selected_dataframe)),
    }


def get_export_state(dataset_id=None):
    return {
        "dataset_id": _resolve_dataset_id(dataset_id),
        "raw_dataset": get_raw_dataset(dataset_id),
        "cleaned_dataset": get_cleaned_dataset(dataset_id),
        "analysis_result": get_analysis_result(dataset_id),
        "prediction_result": get_prediction_result(dataset_id),
        "metadata": get_metadata() if dataset_id is None else (get_dataset_summary(dataset_id) or {}),
    }


def state_summary():
    active_dataset = get_active_dataset_summary()
    datasets = list_dataset_runs()
    return {
        "storage": "sqlite",
        "database": DATABASE_LABEL,
        "active_dataset_id": active_dataset["id"] if active_dataset else None,
        "active_dataset": active_dataset,
        "dataset_count": len(datasets),
        "has_raw_dataset": bool(active_dataset and active_dataset["status"]["has_raw_dataset"]),
        "has_cleaned_dataset": bool(active_dataset and active_dataset["status"]["has_cleaned_dataset"]),
        "has_analysis_result": bool(active_dataset and active_dataset["status"]["has_analysis_result"]),
        "metadata": get_metadata(),
    }
