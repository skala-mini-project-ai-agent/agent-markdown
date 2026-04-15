"""Repository for quality reports."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.schemas.quality_report_schema import QualityReport


class QualityReportRepository:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._records: dict[str, QualityReport] = {}

    def save(self, record: QualityReport) -> QualityReport:
        self._records[record.run_id] = record
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(record), ensure_ascii=True) + "\n")
        return record

    def get(self, run_id: str) -> QualityReport | None:
        return self._records.get(run_id)

