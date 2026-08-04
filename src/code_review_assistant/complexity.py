"""Cyclomatic complexity computation over an AST subtree.

The metric follows McCabe's definition: start at 1 and add one for every
decision point. We count `if`/`elif`, `for`, `while`, `except` handlers,
conditional (ternary) expressions, each boolean sub-expression beyond the
first in an `and`/`or` chain, and each comprehension clause plus its filters.
`elif` is counted automatically because CPython represents it as a nested
`If` node inside `orelse`.
"""
from __future__ import annotations

import ast


class _ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.score = 1

    def visit_If(self, node: ast.If) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # `a and b and c` has two decision points beyond the first operand.
        self.score += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.score += 1 + len(node.ifs)
        self.generic_visit(node)


def cyclomatic_complexity(node: ast.AST) -> int:
    """Return the cyclomatic complexity of the children of ``node``.

    ``node`` is typically a function definition; its own header is not a
    decision point, so we visit its children rather than the node itself.
    Nested functions contribute to the score, matching how most linters
    report a function's total branching cost.
    """
    visitor = _ComplexityVisitor()
    for child in ast.iter_child_nodes(node):
        visitor.visit(child)
    return visitor.score
