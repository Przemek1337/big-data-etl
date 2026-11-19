from pathlib import Path

from check_no_comments import Violation, find_violations, main


def test_reports_trailing_hash_comment():
    assert find_violations("x = 1  # note\n") == [Violation(line=1, kind="comment")]


def test_reports_module_function_and_class_docstrings():
    source = '"""m"""\ndef f():\n    """d"""\n    return 1\nclass C:\n    """c"""\n'
    assert [v.line for v in find_violations(source)] == [1, 3, 6]
    assert {v.kind for v in find_violations(source)} == {"docstring"}


def test_hash_inside_string_is_not_a_comment():
    assert find_violations('url = "http://x/#anchor"\n') == []


def test_main_returns_one_when_any_file_violates(tmp_path):
    clean = tmp_path / "clean.py"
    clean.write_text("x = 1\n")
    dirty = tmp_path / "dirty.py"
    dirty.write_text("# hello\n")
    assert main([str(clean)]) == 0
    assert main([str(clean), str(dirty)]) == 1


def test_repository_python_files_have_no_comments_or_docstrings():
    root = Path(__file__).resolve().parents[2]
    files = [
        str(path)
        for folder in ("src", "scripts", "tests")
        for path in (root / folder).rglob("*.py")
    ]
    assert main(files) == 0
