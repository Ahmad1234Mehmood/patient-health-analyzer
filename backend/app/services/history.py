"""Tiny SQLite store for saved analyses (standard library only - no ORM needed)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class HistoryStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS analyses (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       kind TEXT NOT NULL,
                       subject_id TEXT NOT NULL,
                       summary TEXT NOT NULL,
                       created_at TEXT NOT NULL)"""
            )

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add(self, kind: str, subject_id: str, summary: dict[str, Any]) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO analyses (kind, subject_id, summary, created_at) VALUES (?,?,?,?)",
                (kind, subject_id, json.dumps(summary), datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            return int(cur.lastrowid)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(r), "summary": json.loads(r["summary"])} for r in rows]

    def delete(self, analysis_id: int) -> bool:
        with self._conn() as c:
            return c.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,)).rowcount > 0

    def clear(self) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM analyses")

    def counts(self) -> dict[str, int]:
        with self._conn() as c:
            rows = c.execute("SELECT kind, COUNT(*) n FROM analyses GROUP BY kind").fetchall()
        return {r["kind"]: r["n"] for r in rows}
