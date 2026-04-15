"""SQLite-backed repository for supervisor execution state."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ...schemas.supervisor_state_schema import ApprovalDecision, RetryPlan, SupervisorState


class ExecutionStateRepository:
    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        database_path: str | Path | None = None,
    ) -> None:
        if connection is None:
            connection = sqlite3.connect(str(database_path or ":memory:"))
        connection.row_factory = sqlite3.Row
        self.connection = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS execution_runs (
                run_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS retry_plans (
                run_id TEXT NOT NULL,
                retry_count INTEGER NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, retry_count)
            );
            CREATE TABLE IF NOT EXISTS approval_decisions (
                run_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_state(self, state: SupervisorState) -> None:
        payload = json.dumps(state.to_dict(), ensure_ascii=False)
        now = self._now()
        self.connection.execute(
            """
            INSERT INTO execution_runs (run_id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (state.run_id, payload, now, now),
        )
        self.connection.commit()

    def get_state(self, run_id: str) -> SupervisorState | None:
        row = self.connection.execute(
            "SELECT payload FROM execution_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return SupervisorState.from_dict(json.loads(row["payload"]))

    def save_retry_plan(self, plan: RetryPlan) -> None:
        payload = json.dumps(plan.to_dict(), ensure_ascii=False)
        now = self._now()
        self.connection.execute(
            """
            INSERT INTO retry_plans (run_id, retry_count, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(run_id, retry_count) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (plan.run_id, plan.retry_count, payload, now, now),
        )
        self.connection.commit()

    def latest_retry_plan(self, run_id: str) -> RetryPlan | None:
        row = self.connection.execute(
            """
            SELECT payload FROM retry_plans
            WHERE run_id = ?
            ORDER BY retry_count DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        data = json.loads(row["payload"])
        from ...schemas.supervisor_state_schema import RetryPlan, RetryTarget

        return RetryPlan(
            run_id=data["run_id"],
            retry_targets=[RetryTarget(**target) for target in data.get("retry_targets", [])],
            retry_allowed=bool(data.get("retry_allowed", True)),
            retry_count=int(data.get("retry_count", 0)),
            unresolved_allowed=bool(data.get("unresolved_allowed", False)),
        )

    def save_approval_decision(self, decision: ApprovalDecision) -> None:
        payload = json.dumps(decision.to_dict(), ensure_ascii=False)
        now = self._now()
        self.connection.execute(
            """
            INSERT INTO approval_decisions (run_id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (decision.run_id, payload, now, now),
        )
        self.connection.commit()

    def get_approval_decision(self, run_id: str) -> ApprovalDecision | None:
        row = self.connection.execute(
            "SELECT payload FROM approval_decisions WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return ApprovalDecision.from_dict(json.loads(row["payload"]))
