"""Render FileReports as human-readable text or machine-readable JSON."""
from __future__ import annotations

import json
import sys
from typing import List

from .models import FileReport, Severity

_COLORS = {
    Severity.INFO: "\033[36m",     # cyan
    Severity.LOW: "\033[33m",      # yellow
    Severity.MEDIUM: "\033[35m",   # magenta
    Severity.HIGH: "\033[31m",     # red
}
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"


def _use_color(stream) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


def render_text(reports: List[FileReport], stream=None) -> None:
    stream = stream or sys.stdout
    color = _use_color(stream)

    def paint(text: str, code: str) -> str:
        return f"{code}{text}{_RESET}" if color else text

    total = 0
    counts = {sev: 0 for sev in Severity}
    files_with_issues = 0

    for report in reports:
        if report.error:
            stream.write(paint(f"\n{report.path}: {report.error}\n", _BOLD))
            continue
        issues = report.sorted_issues()
        if not issues:
            continue
        files_with_issues += 1
        stream.write(paint(f"\n{report.path}\n", _BOLD))
        for issue in issues:
            total += 1
            counts[issue.severity] += 1
            sev = paint(f"{issue.severity.label:>6}", _COLORS[issue.severity])
            loc = paint(f"{issue.line}:{issue.column}", _DIM)
            stream.write(f"  {loc}  {sev}  {issue.code}  {issue.message}\n")

    stream.write("\n")
    if total == 0:
        stream.write(paint("No issues found.\n", "\033[32m"))
        return

    summary = "  ".join(
        f"{counts[sev]} {sev.label}" for sev in reversed(Severity) if counts[sev]
    )
    stream.write(
        paint(
            f"Found {total} issue(s) across {files_with_issues} file(s): {summary}\n",
            _BOLD,
        )
    )


def render_json(reports: List[FileReport], stream=None) -> None:
    stream = stream or sys.stdout
    payload = {
        "summary": _summarize(reports),
        "files": [r.to_dict() for r in reports],
    }
    json.dump(payload, stream, indent=2)
    stream.write("\n")


def _summarize(reports: List[FileReport]) -> dict:
    counts = {sev.label: 0 for sev in Severity}
    total = 0
    for report in reports:
        for issue in report.issues:
            counts[issue.severity.label] += 1
            total += 1
    return {
        "files_analyzed": len(reports),
        "total_issues": total,
        "by_severity": counts,
    }
