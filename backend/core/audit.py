"""
core/audit.py

Async SQLite audit logger.
Writes a record for every pipeline run — run_id, query, agent trace,
final outcome. Makes observability concrete and demo-able.
"""

import json
import os
from datetime import datetime

import aiosqlite

from core.config import get_settings

_DB_PATH = get_settings().audit_db_path


async def _ensure_db() -> None:
    os.makedirs(os.path.dirname(_DB_PATH) if os.path.dirname(_DB_PATH) else ".", exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id      TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                user_role   TEXT,
                query       TEXT,
                outcome     TEXT,      -- success | blocked | failed
                agents_fired TEXT,     -- JSON list
                trace       TEXT,      -- JSON full trace
                blocked_reason TEXT
            )
        """)
        await db.commit()


async def log_run(
    *,
    run_id: str,
    user_role: str,
    query: str,
    outcome: str,
    agents_fired: list[str],
    trace: list[dict],
    blocked_reason: str | None = None,
) -> None:
    await _ensure_db()
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO audit_log
                (run_id, timestamp, user_role, query, outcome, agents_fired, trace, blocked_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                datetime.utcnow().isoformat(),
                user_role,
                query,
                outcome,
                json.dumps(agents_fired),
                json.dumps(trace),
                blocked_reason,
            ),
        )
        await db.commit()


async def get_recent_runs(limit: int = 20) -> list[dict]:
    await _ensure_db()
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
