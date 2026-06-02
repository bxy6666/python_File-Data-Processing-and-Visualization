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


def delete_values(connection, keys):
    connection.executemany("DELETE FROM data_state WHERE key = ?", [(key,) for key in keys])


def get_value(key, default=None):
    with database_connection() as connection:
        row = connection.execute("SELECT value FROM data_state WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return deserialize(row[0])


def has_value(key):
    with database_connection() as connection:
        row = connection.execute("SELECT 1 FROM data_state WHERE key = ?", (key,)).fetchone()
    return row is not None


def get_metadata():
    return get_value("metadata", {})


def set_raw_dataset(dataset, metadata=None):
    with database_connection() as connection:
        upsert_value(connection, "raw_dataset", dataset)
        delete_values(connection, ["cleaned_dataset", "analysis_result"])
        upsert_value(connection, "metadata", {"raw": metadata or {}})


def get_raw_dataset():
    return get_value("raw_dataset")


def set_cleaned_dataset(dataset, summary=None):
    metadata = get_metadata()
    metadata["cleaned"] = summary or {}
    with database_connection() as connection:
        upsert_value(connection, "cleaned_dataset", dataset)
        delete_values(connection, ["analysis_result"])
        upsert_value(connection, "metadata", metadata)


def get_cleaned_dataset():
    return get_value("cleaned_dataset")


def set_analysis_result(result, summary=None):
    metadata = get_metadata()
    metadata["analysis"] = summary or {}
    with database_connection() as connection:
        upsert_value(connection, "analysis_result", result)
        upsert_value(connection, "metadata", metadata)


def get_analysis_result():
    return get_value("analysis_result")


def get_export_state():
    return {
        "raw_dataset": get_raw_dataset(),
        "cleaned_dataset": get_cleaned_dataset(),
        "analysis_result": get_analysis_result(),
        "metadata": get_metadata(),
    }


def state_summary():
    return {
        "storage": "sqlite",
        "database": DATABASE_LABEL,
        "has_raw_dataset": has_value("raw_dataset"),
        "has_cleaned_dataset": has_value("cleaned_dataset"),
        "has_analysis_result": has_value("analysis_result"),
        "metadata": get_metadata(),
    }
