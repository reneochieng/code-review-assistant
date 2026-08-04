"""Command-line entry point for code-review-assistant."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .analyzer import analyze_paths
from .config import Config
from .models import FileReport, Severity
from .reporters import render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-review",
        description="Static analysis for Python: flags bugs, style smells, and complexity.",
    )
    parser.add_argument("paths", nargs="+", help="files or directories to analyze")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument(
        "--min-severity",
        choices=[s.label for s in Severity],
        default="info",
        help="hide findings below this severity (default: info)",
    )
    parser.add_argument("--max-complexity", type=int, default=10,
                        help="cyclomatic complexity threshold (default: 10)")
    parser.add_argument("--max-function-lines", type=int, default=50,
                        help="function length threshold in lines (default: 50)")
    parser.add_argument("--max-arguments", type=int, default=6,
                        help="argument-count threshold (default: 6)")
    parser.add_argument("--exit-zero", action="store_true",
                        help="always exit 0, even when issues are found")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _has_issues(reports: List[FileReport]) -> bool:
    return any(r.issues or r.error for r in reports)


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    config = Config(
        max_complexity=args.max_complexity,
        max_function_lines=args.max_function_lines,
        max_arguments=args.max_arguments,
        min_severity=Severity.from_label(args.min_severity),
    )
    reports = analyze_paths(args.paths, config)

    if args.json:
        render_json(reports)
    else:
        render_text(reports)

    if args.exit_zero:
        return 0
    return 1 if _has_issues(reports) else 0


if __name__ == "__main__":
    sys.exit(main())
