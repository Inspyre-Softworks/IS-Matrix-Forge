"""
Package-wide import smoke test.

Imports every module under ``is_matrix_forge`` so that syntax errors,
missing dependencies, and broken imports are caught even in modules no
other test touches. Hardware access is not required: the device helper
resolves ``DEVICES`` lazily.
"""
from __future__ import annotations

import importlib
import pkgutil

import pytest

import is_matrix_forge


def _walk_module_names() -> list[str]:
    names = []
    for module_info in pkgutil.walk_packages(
        is_matrix_forge.__path__, prefix=f'{is_matrix_forge.__name__}.'
    ):
        names.append(module_info.name)
    return sorted(names)


@pytest.mark.parametrize('module_name', _walk_module_names())
def test_module_imports(module_name):
    importlib.import_module(module_name)
