"""
Package-wide import smoke test.

Imports every module under ``is_matrix_forge`` so that syntax errors,
missing dependencies, and broken imports are caught even in modules no
other test touches. Hardware access is not required: the device helper
resolves ``DEVICES`` lazily.

The imports run in a clean subprocess because several legacy test
modules install ``sys.modules`` stubs at collection time (e.g. for
``is_matrix_forge.led_matrix.helpers.device``), which would otherwise
break importing real subpackages in this process.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import is_matrix_forge

_IMPORT_ALL = textwrap.dedent(
    """
    import importlib
    import sys
    from pathlib import Path

    import is_matrix_forge

    pkg_root = Path(is_matrix_forge.__file__).parent
    names = set()
    for py_file in pkg_root.rglob('*.py'):
        rel = py_file.relative_to(pkg_root.parent).with_suffix('')
        parts = list(rel.parts)
        if parts[-1] == '__init__':
            parts = parts[:-1]
        if '__pycache__' in parts:
            continue
        names.add('.'.join(parts))

    failures = []
    for name in sorted(names):
        try:
            importlib.import_module(name)
        except Exception as e:  # noqa: BLE001 -- report every kind of import failure
            failures.append(f'{name}: {type(e).__name__}: {e}')

    print(f'checked {len(names)} modules')
    if failures:
        print('FAILURES:')
        print('\\n'.join(failures))
        sys.exit(1)
    """
)


def test_every_module_imports():
    repo_root = Path(is_matrix_forge.__file__).parent.parent
    result = subprocess.run(
        [sys.executable, '-c', _IMPORT_ALL],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f'importing the package failed:\n{result.stdout}\n{result.stderr}'
    )
