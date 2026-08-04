"""Unit tests for the cyclomatic complexity metric."""
import ast

from code_review_assistant.complexity import cyclomatic_complexity


def _complexity(source):
    tree = ast.parse(source)
    func = tree.body[0]
    return cyclomatic_complexity(func)


def test_straight_line_is_one():
    assert _complexity("def f():\n    return 1\n") == 1


def test_single_if_adds_one():
    assert _complexity("def f(x):\n    if x:\n        return 1\n    return 0\n") == 2


def test_boolean_operators_count():
    # base 1 + one `if` + two extra boolean operands (a and b and c) = 4
    assert _complexity("def f(a, b, c):\n    if a and b and c:\n        return 1\n    return 0\n") == 4


def test_loop_and_except():
    src = (
        "def f(xs):\n"
        "    for x in xs:\n"          # +1
        "        try:\n"
        "            do(x)\n"
        "        except ValueError:\n"  # +1
        "            pass\n"
    )
    assert _complexity(src) == 3


def test_comprehension_with_filter():
    # base 1 + comprehension (+1) + its if (+1) = 3
    assert _complexity("def f(xs):\n    return [x for x in xs if x]\n") == 3
