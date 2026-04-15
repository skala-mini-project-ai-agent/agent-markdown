"""Report output schema for the Technology Strategy Analysis Service."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass(slots=True)
class EvidenceTrace:
    """Trace link from a report claim to its source evidence."""

    claim_id: str
    evidence_id: str
    source_name: str
    url: str
    published_at: str
    quote: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceTrace":
        return cls(
            claim_id=data["claim_id"],
            evidence_id=data["evidence_id"],
            source_name=data["source_name"],
            url=data["url"],
            published_at=data["published_at"],
            quote=data.get("quote", ""),
        )


@dataclass(slots=True)
class ReportSection:
    """A single section in the generated report."""

    section_id: str
    title: str
    body: str
    claim_ids: list[str] = field(default_factory=list)
    subsections: list["ReportSection"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["subsections"] = [s.to_dict() for s in self.subsections]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSection":
        return cls(
            section_id=data["section_id"],
            title=data["title"],
            body=data["body"],
            claim_ids=list(data.get("claim_ids", [])),
            subsections=[cls.from_dict(s) for s in data.get("subsections", [])],
        )


@dataclass(slots=True)
class ReportWarning:
    """A warning or limitation attached to the report."""

    code: str
    message: str
    affected_cells: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportWarning":
        return cls(
            code=data["code"],
            message=data["message"],
            affected_cells=list(data.get("affected_cells", [])),
        )


@dataclass(slots=True)
class ReportOutput:
    """Top-level report artifact produced by ReportGenerationAgent."""

    report_id: str
    run_id: str
    format: ReportFormat
    status: ReportStatus
    sections: list[ReportSection]
    reference_trace: list[EvidenceTrace]
    warnings: list[ReportWarning]
    output_path: str
    html_path: str = ""
    pdf_path: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "run_id": self.run_id,
            "format": self.format.value,
            "status": self.status.value,
            "sections": [s.to_dict() for s in self.sections],
            "reference_trace": [t.to_dict() for t in self.reference_trace],
            "warnings": [w.to_dict() for w in self.warnings],
            "output_path": self.output_path,
            "html_path": self.html_path,
            "pdf_path": self.pdf_path,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportOutput":
        return cls(
            report_id=data["report_id"],
            run_id=data["run_id"],
            format=ReportFormat(data["format"]),
            status=ReportStatus(data["status"]),
            sections=[ReportSection.from_dict(s) for s in data.get("sections", [])],
            reference_trace=[EvidenceTrace.from_dict(t) for t in data.get("reference_trace", [])],
            warnings=[ReportWarning.from_dict(w) for w in data.get("warnings", [])],
            output_path=data.get("output_path", ""),
            html_path=data.get("html_path", ""),
            pdf_path=data.get("pdf_path", ""),
            created_at=data.get("created_at", ""),
            metadata=dict(data.get("metadata", {})),
        )
