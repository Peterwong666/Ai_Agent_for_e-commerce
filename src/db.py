"""SQLite 数据库: 保存分析历史记录."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"


@contextmanager
def _get_conn() -> sqlite3.Connection:
    """获取数据库连接, 自动创建表和数据库."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                market TEXT,
                category_name TEXT,
                file_name TEXT,
                product_count INTEGER,
                total_score REAL,
                level TEXT,
                metrics_json TEXT,
                scoring_json TEXT,
                risk_json TEXT,
                report_markdown TEXT
            )
        """)
        conn.commit()
        yield conn
    finally:
        conn.close()


def save_analysis_run(
    market: str,
    category_name: str,
    file_name: str,
    product_count: int,
    total_score: float,
    level: str,
    metrics_json: dict,
    scoring_json: dict,
    risk_json: dict,
    report_markdown: str,
) -> int:
    """保存一次分析记录, 返回记录 ID."""
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO analysis_runs
               (created_at, market, category_name, file_name, product_count,
                total_score, level, metrics_json, scoring_json, risk_json, report_markdown)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                now, market, category_name, file_name, product_count,
                total_score, level,
                json.dumps(metrics_json, ensure_ascii=False),
                json.dumps(scoring_json, ensure_ascii=False),
                json.dumps(risk_json, ensure_ascii=False),
                report_markdown,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def list_analysis_runs(limit: int = 20) -> list[dict]:
    """列出最近的分析记录."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, created_at, market, category_name, product_count, total_score, level "
            "FROM analysis_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_analysis_run(run_id: int) -> dict | None:
    """获取单条分析记录详情."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM analysis_runs WHERE id = ?", (run_id,)
        ).fetchone()
    if row is None:
        return None
    return dict(row)
