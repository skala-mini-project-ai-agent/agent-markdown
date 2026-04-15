"""Persist normalized evidence through repository interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.schemas.normalized_evidence_schema import NormalizedEvidence


@dataclass(slots=True)
class EvidenceLoader:
    repository: object

    def load(self, evidence: Iterable[NormalizedEvidence]) -> list[NormalizedEvidence]:
        records = list(evidence)
        if hasattr(self.repository, "save_many"):
            self.repository.save_many(records)
        elif hasattr(self.repository, "save"):
            for record in records:
                self.repository.save(record)
        return records

