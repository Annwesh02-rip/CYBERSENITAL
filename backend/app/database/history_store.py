"""SQLite storage for CyberSentinel analysis history."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

DB_FILE = (
    ROOT / "backend" / "data"
    / "analysis_history.sqlite3"
)


def connect():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DB_FILE,
        timeout=15
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_history_db():
    with connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                rows_analyzed INTEGER NOT NULL,
                flagged_original INTEGER NOT NULL,
                flagged_pca INTEGER NOT NULL,
                has_labels INTEGER NOT NULL,
                result_json TEXT NOT NULL
            )
        """)


def save_analysis(result):
    init_history_db()

    timestamp = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    serialized = json.dumps(
        result,
        ensure_ascii=True,
        allow_nan=False
    )

    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO analysis_runs (
                created_at,
                source,
                rows_analyzed,
                flagged_original,
                flagged_pca,
                has_labels,
                result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                result["source"],
                int(result["rows_analyzed"]),
                int(result["flagged_original"]),
                int(result["flagged_pca"]),
                int(bool(result["has_labels"])),
                serialized
            )
        )

        run_id = cursor.lastrowid

    return {
        **result,
        "history_id": run_id,
        "created_at": timestamp
    }


def list_analyses(limit=30):
    init_history_db()

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                created_at,
                source,
                rows_analyzed,
                flagged_original,
                flagged_pca,
                has_labels
            FROM analysis_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        total = connection.execute(
            "SELECT COUNT(*) FROM analysis_runs"
        ).fetchone()[0]

    return {
        "total": total,
        "runs": [dict(row) for row in rows]
    }


def get_analysis(run_id):
    init_history_db()

    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, created_at, result_json
            FROM analysis_runs
            WHERE id = ?
            """,
            (run_id,)
        ).fetchone()

    if row is None:
        return None

    result = json.loads(row["result_json"])

    return {
        **result,
        "history_id": row["id"],
        "created_at": row["created_at"]
    }


def delete_analysis(run_id):
    init_history_db()

    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM analysis_runs WHERE id = ?",
            (run_id,)
        )

        return cursor.rowcount > 0