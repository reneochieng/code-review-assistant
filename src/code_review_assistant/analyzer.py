"""Orchestration: turn source text or file paths into FileReports."""
from __future__ import annotations

import ast
import os
from typing import Iterable, List

from . import checks
from .config import Config
from .models import FileReport, Issue


def analyze_source(path: str, source: str, config: Config | None = None) -> FileReport:
    """Analyze a single source string and return its FileReport."""
    config = config or Config()
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return FileReport(path=path, error=f"syntax error: {exc.msg} (line {exc.lineno})")

    lines = source.splitlines()
    issues: List[Issue] = []
    issues += checks.check_star_imports(tree)
    issues += checks.check_unused_imports(tree)
    issues += checks.check_comparisons(tree)
    issues += checks.check_bare_except(tree)
    issues += checks.check_builtin_assignments(tree)
    issues += checks.check_todos(lines)
    issues += checks.check_definitions(tree, config)

    issues = [i for i in issues if i.severity >= config.min_severity]
    return FileReport(path=path, issues=issues)


def analyze_file(path: str, config: Config | None = None) -> FileReport:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        return FileReport(path=path, error=f"could not read file: {exc}")
    return analyze_source(path, source, config)


def _iter_python_files(paths: Iterable[str]) -> Iterable[str]:
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                # skip common noise directories
                dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".venv", "venv", "build", "dist"}]
                for name in sorted(files):
                    if name.endswith(".py"):
                        yield os.path.join(root, name)
        else:
            yield path


def analyze_paths(paths: Iterable[str], config: Config | None = None) -> List[FileReport]:
    """Analyze every ``.py`` file reachable from ``paths`` (files or dirs)."""
    config = config or Config()
    reports: List[FileReport] = []
    for file_path in _iter_python_files(paths):
        reports.append(analyze_file(file_path, config))
    return reports
