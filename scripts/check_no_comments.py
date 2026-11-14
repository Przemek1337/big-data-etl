import ast
import io
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True)
class Violation:
    line: int
    kind: Literal["comment", "docstring"]


def _comment_violations(source: str) -> list[Violation]:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return [
        Violation(token.start[0], "comment") for token in tokens if token.type == tokenize.COMMENT
    ]


def _docstring_violations(source: str) -> list[Violation]:
    violations: list[Violation] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, DOCSTRING_OWNERS) or not node.body:
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            violations.append(Violation(first.lineno, "docstring"))
    return violations


def find_violations(source: str) -> list[Violation]:
    violations = _comment_violations(source) + _docstring_violations(source)
    return sorted(violations, key=lambda violation: violation.line)


def main(argv: list[str]) -> int:
    exit_code = 0
    for name in argv:
        source = Path(name).read_text(encoding="utf-8")
        for violation in find_violations(source):
            sys.stderr.write(f"{name}:{violation.line} {violation.kind}\n")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
