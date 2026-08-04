"""Core data types shared across the analyzer."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List


class Severity(IntEnum):
    """Ordered severity levels. Higher is worse; ordering enables filtering."""

    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @property
    def label(self) -> str:
        return self.name.lower()

    @classmethod
    def from_label(cls, label: str) -> "Severity":
        try:
            return cls[label.upper()]
        except KeyError as exc:
            raise ValueError(f"unknown severity: {label!r}") from exc


@dataclass(frozen=True)
class Issue:
    """A single finding at a specific source location."""

    code: str          # stable identifier, e.g. "CRA001"
    message: str       # human-readable explanation
    line: int          # 1-based line number
    column: int        # 0-based column offset
    severity: Severity
    symbol: str = ""   # the name/symbol involved, when relevant

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "severity": self.severity.label,
            "symbol": self.symbol,
        }


@dataclass
class FileReport:
    """All findings for one analyzed file (or a parse error)."""

    path: str
    issues: List[Issue] = field(default_factory=list)
    error: str = ""  # non-empty when the file could not be parsed

    @property
    def ok(self) -> bool:
        return not self.error and not self.issues

    def sorted_issues(self) -> List[Issue]:
        return sorted(self.issues, key=lambda i: (i.line, i.column, i.code))

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "error": self.error,
            "issues": [i.to_dict() for i in self.sorted_issues()],
        }
