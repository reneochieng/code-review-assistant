"""Individual static-analysis checks, each emitting zero or more Issues.

Every check has a stable code (CRAxxx) so findings can be tracked, filtered,
or suppressed over time. Checks operate purely on the AST plus the raw source
lines; there is no execution of the analyzed code.
"""
from __future__ import annotations

import ast
import builtins
import re
from typing import Iterable, List

from .complexity import cyclomatic_complexity
from .config import Config
from .models import Issue, Severity

_BUILTIN_NAMES = {name for name in dir(builtins) if not name.startswith("_")}
_TODO_RE = re.compile(r"#.*\b(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)


def _docstring_missing(node: ast.AST) -> bool:
    return ast.get_docstring(node) is None


def _is_public(name: str) -> bool:
    return not name.startswith("_")


# --- module / expression level ------------------------------------------------

def check_star_imports(tree: ast.Module) -> List[Issue]:
    """CRA011: `from x import *` pollutes the namespace and hides origins."""
    issues: List[Issue] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if any(alias.name == "*" for alias in node.names):
                issues.append(
                    Issue(
                        code="CRA011",
                        message=f"star import from '{node.module or ''}' pollutes the namespace",
                        line=node.lineno,
                        column=node.col_offset,
                        severity=Severity.MEDIUM,
                        symbol=node.module or "*",
                    )
                )
    return issues


def check_unused_imports(tree: ast.Module) -> List[Issue]:
    """CRA004: an imported name that is never referenced in the module."""
    used: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            # The root of an attribute chain (a in a.b.c) is a Name node,
            # already captured above; nothing extra needed here.
            pass

    imported: list = []  # (name, node)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imported.append((name, node))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                imported.append((name, node))

    issues: List[Issue] = []
    for name, node in imported:
        if name not in used:
            issues.append(
                Issue(
                    code="CRA004",
                    message=f"'{name}' imported but never used",
                    line=node.lineno,
                    column=node.col_offset,
                    severity=Severity.LOW,
                    symbol=name,
                )
            )
    return issues


def check_comparisons(tree: ast.Module) -> List[Issue]:
    """CRA003 / CRA013: `== None` and `type(x) == T` anti-patterns."""
    issues: List[Issue] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)):
                if isinstance(comparator, ast.Constant) and comparator.value is None:
                    suggestion = "is" if isinstance(op, ast.Eq) else "is not"
                    issues.append(
                        Issue(
                            code="CRA003",
                            message=f"comparison to None should use '{suggestion}', not '==' / '!='",
                            line=node.lineno,
                            column=node.col_offset,
                            severity=Severity.LOW,
                            symbol="None",
                        )
                    )
        # type(x) == something  ->  isinstance
        if isinstance(node.left, ast.Call) and _is_type_call(node.left):
            if any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
                issues.append(
                    Issue(
                        code="CRA013",
                        message="use isinstance() instead of comparing type() results",
                        line=node.lineno,
                        column=node.col_offset,
                        severity=Severity.LOW,
                        symbol="type",
                    )
                )
    return issues


def _is_type_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id == "type" and len(call.args) == 1


def check_bare_except(tree: ast.Module) -> List[Issue]:
    """CRA002: a bare `except:` swallows every exception, including SystemExit."""
    issues: List[Issue] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(
                Issue(
                    code="CRA002",
                    message="bare 'except:' catches everything; catch a specific exception",
                    line=node.lineno,
                    column=node.col_offset,
                    severity=Severity.MEDIUM,
                    symbol="except",
                )
            )
    return issues


def check_todos(source_lines: Iterable[str]) -> List[Issue]:
    """CRA012: TODO / FIXME / XXX / HACK markers left in comments."""
    issues: List[Issue] = []
    for lineno, text in enumerate(source_lines, start=1):
        match = _TODO_RE.search(text)
        if match:
            issues.append(
                Issue(
                    code="CRA012",
                    message=f"unresolved '{match.group(1).upper()}' marker in comment",
                    line=lineno,
                    column=match.start(),
                    severity=Severity.INFO,
                    symbol=match.group(1).upper(),
                )
            )
    return issues


def check_builtin_assignments(tree: ast.Module) -> List[Issue]:
    """CRA010: assigning to a name that shadows a builtin (e.g. `list = ...`)."""
    issues: List[Issue] = []
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id in _BUILTIN_NAMES:
                issues += _check_builtin_shadow(target.id, target.lineno, target.col_offset)
    return issues


# --- function / class level ---------------------------------------------------

_FUNC_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef)


def check_definitions(tree: ast.Module, config: Config) -> List[Issue]:
    """Run all per-definition checks (functions and classes)."""
    issues: List[Issue] = []
    for node in ast.walk(tree):
        if isinstance(node, _FUNC_TYPES):
            issues += _check_function(node, config)
        elif isinstance(node, ast.ClassDef):
            issues += _check_class(node)
    return issues


def _check_function(node, config: Config) -> List[Issue]:
    issues: List[Issue] = []
    name = node.name

    # CRA001 -- mutable default arguments
    for default in node.args.defaults + node.args.kw_defaults:
        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
            issues.append(
                Issue(
                    code="CRA001",
                    message=f"mutable default argument in '{name}' is shared across calls",
                    line=default.lineno,
                    column=default.col_offset,
                    severity=Severity.HIGH,
                    symbol=name,
                )
            )

    # CRA006 -- missing docstring on a public definition
    if _is_public(name) and _docstring_missing(node):
        issues.append(
            Issue(
                code="CRA006",
                message=f"public function '{name}' is missing a docstring",
                line=node.lineno,
                column=node.col_offset,
                severity=Severity.INFO,
                symbol=name,
            )
        )

    # CRA007 -- function too long
    span = _line_span(node)
    if span > config.max_function_lines:
        issues.append(
            Issue(
                code="CRA007",
                message=f"function '{name}' is {span} lines long (max {config.max_function_lines})",
                line=node.lineno,
                column=node.col_offset,
                severity=Severity.MEDIUM,
                symbol=name,
            )
        )

    # CRA008 -- too many arguments
    arg_count = _argument_count(node)
    if arg_count > config.max_arguments:
        issues.append(
            Issue(
                code="CRA008",
                message=f"function '{name}' takes {arg_count} arguments (max {config.max_arguments})",
                line=node.lineno,
                column=node.col_offset,
                severity=Severity.LOW,
                symbol=name,
            )
        )

    # CRA009 -- high cyclomatic complexity
    complexity = cyclomatic_complexity(node)
    if complexity > config.max_complexity:
        severity = Severity.HIGH if complexity > config.max_complexity * 2 else Severity.MEDIUM
        issues.append(
            Issue(
                code="CRA009",
                message=f"function '{name}' has cyclomatic complexity {complexity} (max {config.max_complexity})",
                line=node.lineno,
                column=node.col_offset,
                severity=severity,
                symbol=name,
            )
        )

    # CRA010 -- shadowing a builtin via the function name or its arguments
    issues += _check_builtin_shadow(name, node.lineno, node.col_offset)
    for arg in _all_args(node):
        issues += _check_builtin_shadow(arg.arg, arg.lineno, arg.col_offset)

    # CRA005 -- unused local variables
    issues += _check_unused_locals(node)

    return issues


def _check_class(node: ast.ClassDef) -> List[Issue]:
    issues: List[Issue] = []
    if _is_public(node.name) and _docstring_missing(node):
        issues.append(
            Issue(
                code="CRA006",
                message=f"public class '{node.name}' is missing a docstring",
                line=node.lineno,
                column=node.col_offset,
                severity=Severity.INFO,
                symbol=node.name,
            )
        )
    issues += _check_builtin_shadow(node.name, node.lineno, node.col_offset)
    return issues


def _check_builtin_shadow(name: str, line: int, column: int) -> List[Issue]:
    if name in _BUILTIN_NAMES:
        return [
            Issue(
                code="CRA010",
                message=f"'{name}' shadows a Python builtin",
                line=line,
                column=column,
                severity=Severity.LOW,
                symbol=name,
            )
        ]
    return []


def _check_unused_locals(func) -> List[Issue]:
    """CRA005: a simple local assignment whose value is never read.

    Conservative on purpose to avoid false positives: only single-target
    ``name = ...`` assignments are considered, names starting with ``_`` are
    ignored (conventional 'unused'), and any load of the name anywhere in the
    function -- including nested scopes -- counts as a use.
    """
    assigned: dict = {}
    loaded: set = set()
    declared: set = set()

    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loaded.add(node.id)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            declared.update(node.names)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                assigned.setdefault(target.id, target)

    issues: List[Issue] = []
    for name, target in assigned.items():
        if name.startswith("_") or name in loaded or name in declared:
            continue
        issues.append(
            Issue(
                code="CRA005",
                message=f"local variable '{name}' is assigned but never used",
                line=target.lineno,
                column=target.col_offset,
                severity=Severity.LOW,
                symbol=name,
            )
        )
    return issues


# --- small AST helpers --------------------------------------------------------

def _line_span(node) -> int:
    end = getattr(node, "end_lineno", None)
    if end is None:
        return 1
    return end - node.lineno + 1


def _all_args(node) -> List[ast.arg]:
    a = node.args
    args = list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)
    if a.vararg:
        args.append(a.vararg)
    if a.kwarg:
        args.append(a.kwarg)
    return args


def _argument_count(node) -> int:
    a = node.args
    count = len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs)
    if a.vararg:
        count += 1
    if a.kwarg:
        count += 1
    return count
