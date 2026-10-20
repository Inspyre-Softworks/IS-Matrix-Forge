from __future__ import annotations

import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "is_matrix_forge"


def test_all_package_modules_parse() -> None:
    failures: list[str] = []

    for path in PACKAGE_ROOT.rglob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(PACKAGE_ROOT)}:{exc.lineno}: {exc.msg}")

    assert not failures, "Package modules with invalid syntax:\n" + "\n".join(failures)
