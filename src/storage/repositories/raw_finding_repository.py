"""Repository for raw findings."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.schemas.raw_result_schema import RawFinding


class RawFindingRepository:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._records: dict[str, list[RawFinding]] = {}

    def save_many(self, records: list[RawFinding]) -> list[RawFinding]:
        for record in records:
            self.save(record)
        return records

    def save(self, record: RawFinding) -> RawFinding:
        self._records.setdefault(record.run_id, []).append(record)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(record), ensure_ascii=True) + "\n")
        return record

    def list_by_run(self, run_id: str) -> list[RawFinding]:
        return list(self._records.get(run_id, []))

    def all(self) -> list[RawFinding]:
        return [record for records in self._records.values() for record in records]

