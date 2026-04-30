from __future__ import annotations

from importlib import metadata
from pathlib import Path
from typing import Optional

import tomllib


PACKAGE_NAME = "IS-Matrix-Forge"


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_source_version() -> Optional[str]:
    pyproject_path = get_project_root() / "pyproject.toml"
    if not pyproject_path.is_file():
        return None

    try:
        with pyproject_path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError:
        return None

    return data.get("tool", {}).get("poetry", {}).get("version")


def get_installed_version(package_name: str = PACKAGE_NAME) -> Optional[str]:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def get_version_snapshot() -> dict[str, Optional[str]]:
    source_version = get_source_version()
    installed_version = get_installed_version()
    display_version = source_version or installed_version or "unknown"

    return {
        "package_name": PACKAGE_NAME,
        "display_version": display_version,
        "source_version": source_version,
        "installed_version": installed_version,
    }
