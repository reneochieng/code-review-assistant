"""End-to-end tests over the sample file and directory walking."""
import os

from code_review_assistant import analyze_paths, analyze_source

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")


def test_sample_file_flags_multiple_issues():
    reports = analyze_paths([os.path.join(EXAMPLES, "sample_bad.py")])
    assert len(reports) == 1
    codes = {i.code for i in reports[0].issues}
    for expected in {"CRA001", "CRA002", "CRA003", "CRA004", "CRA008", "CRA011", "CRA012"}:
        assert expected in codes, f"expected {expected} in {sorted(codes)}"


def test_clean_source_has_no_issues():
    src = (
        "def add(a, b):\n"
        '    """Return the sum of a and b."""\n'
        "    return a + b\n"
    )
    report = analyze_source("clean.py", src)
    assert report.ok


def test_directory_walk_finds_python_files():
    reports = analyze_paths([EXAMPLES])
    assert any(r.path.endswith("sample_bad.py") for r in reports)
