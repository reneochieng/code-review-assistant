"""code-review-assistant: a static-analysis tool for reviewing Python code.

Public API:
    analyze_source(path, source, config) -> FileReport
    analyze_paths(paths, config)         -> list[FileReport]
"""
from .models import Issue, Severity, FileReport
from .config import Config
from .analyzer import analyze_source, analyze_paths

__version__ = "0.1.0"

__all__ = [
    "Issue",
    "Severity",
    "FileReport",
    "Config",
    "analyze_source",
    "analyze_paths",
    "__version__",
]
