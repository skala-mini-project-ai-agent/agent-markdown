"""SQLite-backed repository for report artifacts."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ...schemas.report_output_schema import ReportOutput


class ReportRepository:
    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        database_path: str | Path | None = None,
    ) -> None:
        if connection is None:
            if database_path is None:
                database_path = ":memory:"
            connection = sqlite3.connect(str(database_path))
        connection.row_factory = sqlite3.Row
        self.connection = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                format TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                output_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_reports_run_id ON reports (run_id);
            """
        )
        self.connection.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save(self, report: ReportOutput) -> None:
        payload = json.dumps(report.to_dict(), ensure_ascii=False)
        now = self._now()
        self.connection.execute(
            """
            INSERT INTO reports (report_id, run_id, format, status, payload, output_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET
                status = excluded.status,
                payload = excluded.payload,
                output_path = excluded.output_path,
                updated_at = excluded.updated_at
            """,
            (
                report.report_id,
                report.run_id,
                report.format.value,
                report.status.value,
                payload,
                report.output_path,
                report.created_at or now,
                now,
            ),
        )
        self.connection.commit()

    def get(self, report_id: str) -> ReportOutput | None:
        row = self.connection.execute(
            "SELECT payload FROM reports WHERE report_id = ?",
            (report_id,),
        ).fetchone()
        if row is None:
            return None
        return ReportOutput.from_dict(json.loads(row["payload"]))

    def list_by_run(self, run_id: str) -> list[ReportOutput]:
        rows = self.connection.execute(
            "SELECT payload FROM reports WHERE run_id = ? ORDER BY created_at DESC",
            (run_id,),
        ).fetchall()
        return [ReportOutput.from_dict(json.loads(row["payload"])) for row in rows]

    def latest_for_run(self, run_id: str) -> ReportOutput | None:
        reports = self.list_by_run(run_id)
        return reports[0] if reports else None
