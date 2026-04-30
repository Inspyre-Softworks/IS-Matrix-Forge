from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()
TEXT_SUFFIXES = {".md", ".py", ".toml", ".json", ".yml", ".yaml", ".txt"}
BANNED_SNIPPETS = (
    "Inspyre-Softworks/led-matrix-battery",
    "led-matrix-battery",
    "grew out of the LED Matrix project",
)


def _tracked_text_files() -> list[Path]:
    results = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if "__pycache__" in path.parts:
            continue
        if path.resolve() == THIS_FILE:
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            results.append(path)
    return results


def test_tracked_files_do_not_reference_the_old_project_identity():
    offenders: list[str] = []

    for path in _tracked_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for snippet in BANNED_SNIPPETS:
            if snippet in text:
                offenders.append(f"{path.relative_to(ROOT)} -> {snippet}")

    assert not offenders, "Old project references remain in tracked files:\n" + "\n".join(offenders)
