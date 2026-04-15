"""Repository for normalized evidence."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.schemas.normalized_evidence_schema import NormalizedEvidence


class NormalizedEvidenceRepository:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._records: dict[str, list[NormalizedEvidence]] = {}

    def save_many(self, records: list[NormalizedEvidence]) -> list[NormalizedEvidence]:
        for record in records:
            self.save(record)
        return records

    def save(self, record: NormalizedEvidence) -> NormalizedEvidence:
        self._records.setdefault(record.run_id, []).append(record)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(record), ensure_ascii=True) + "\n")
        return record

    def list_by_run(self, run_id: str) -> list[NormalizedEvidence]:
        return list(self._records.get(run_id, []))

