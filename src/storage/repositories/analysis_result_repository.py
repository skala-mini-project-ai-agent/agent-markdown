"""SQLite-backed repository for analysis results."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from ...schemas.analysis_output_schema import (
    ConflictResolutionResult,
    MergedAnalysisResult,
    PriorityMatrixRow,
    TRLAnalysisResult,
    ThreatAnalysisResult,
)


class AnalysisResultRepository:
    def __init__(self, connection: sqlite3.Connection | None = None, database_path: str | Path | None = None):
        if connection is None:
            if database_path is None:
                database_path = ":memory:"
            connection = sqlite3.connect(str(database_path))
        connection.row_factory = sqlite3.Row
        self.connection = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cursor = self.connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS trl_analysis_results (
                run_id TEXT NOT NULL,
                technology TEXT NOT NULL,
                company TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, technology, company)
            );
            CREATE TABLE IF NOT EXISTS threat_analysis_results (
                run_id TEXT NOT NULL,
                technology TEXT NOT NULL,
                company TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, technology, company)
            );
            CREATE TABLE IF NOT EXISTS conflict_resolution_results (
                run_id TEXT NOT NULL,
                technology TEXT NOT NULL,
                company TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, technology, company)
            );
            CREATE TABLE IF NOT EXISTS merged_analysis_results (
                run_id TEXT NOT NULL,
                technology TEXT NOT NULL,
                company TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, technology, company)
            );
            CREATE TABLE IF NOT EXISTS priority_matrix_rows (
                run_id TEXT NOT NULL,
                technology TEXT NOT NULL,
                company TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, technology, company)
            );
            """
        )
        self.connection.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _upsert(self, table: str, result: object) -> None:
        payload = json.dumps(asdict(result), ensure_ascii=False)
        key = (result.run_id, result.technology, result.company)  # type: ignore[attr-defined]
        timestamp = self._now()
        self.connection.execute(
            f"""
            INSERT INTO {table} (run_id, technology, company, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, technology, company) DO UPDATE SET
                payload = excluded.payload,
                updated_at = excluded.updated_at
            """,
            (*key, payload, timestamp, timestamp),
        )
        self.connection.commit()

    def _fetch_one(self, table: str, run_id: str, technology: str, company: str) -> dict | None:
        row = self.connection.execute(
            f"SELECT payload FROM {table} WHERE run_id = ? AND technology = ? AND company = ?",
            (run_id, technology, company),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["payload"])

    def store_trl_result(self, result: TRLAnalysisResult) -> None:
        self._upsert("trl_analysis_results", result)

    def store_threat_result(self, result: ThreatAnalysisResult) -> None:
        self._upsert("threat_analysis_results", result)

    def store_conflict_result(self, result: ConflictResolutionResult) -> None:
        self._upsert("conflict_resolution_results", result)

    def store_merged_result(self, result: MergedAnalysisResult) -> None:
        self._upsert("merged_analysis_results", result)

    def store_priority_rows(self, rows: Sequence[PriorityMatrixRow]) -> None:
        for row in rows:
            self._upsert("priority_matrix_rows", row)

    def get_trl_result(self, run_id: str, technology: str, company: str) -> TRLAnalysisResult | None:
        payload = self._fetch_one("trl_analysis_results", run_id, technology, company)
        return None if payload is None else TRLAnalysisResult.from_dict(payload)

    def get_threat_result(self, run_id: str, technology: str, company: str) -> ThreatAnalysisResult | None:
        payload = self._fetch_one("threat_analysis_results", run_id, technology, company)
        return None if payload is None else ThreatAnalysisResult.from_dict(payload)

    def get_conflict_result(self, run_id: str, technology: str, company: str) -> ConflictResolutionResult | None:
        payload = self._fetch_one("conflict_resolution_results", run_id, technology, company)
        return None if payload is None else ConflictResolutionResult.from_dict(payload)

    def get_merged_result(self, run_id: str, technology: str, company: str) -> MergedAnalysisResult | None:
        payload = self._fetch_one("merged_analysis_results", run_id, technology, company)
        return None if payload is None else MergedAnalysisResult.from_dict(payload)

    def list_priority_rows(self, run_id: str) -> list[PriorityMatrixRow]:
        rows = self.connection.execute(
            "SELECT payload FROM priority_matrix_rows WHERE run_id = ? ORDER BY technology, company",
            (run_id,),
        ).fetchall()
        return [PriorityMatrixRow.from_dict(json.loads(row["payload"])) for row in rows]

