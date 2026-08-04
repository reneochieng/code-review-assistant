"""User-tunable thresholds and filters for an analysis run."""
from __future__ import annotations

from dataclasses import dataclass

from .models import Severity


@dataclass
class Config:
    max_complexity: int = 10      # cyclomatic complexity above this is flagged
    max_function_lines: int = 50  # function line-span above this is flagged
    max_arguments: int = 6        # argument count above this is flagged
    min_severity: Severity = Severity.INFO  # drop findings below this level
