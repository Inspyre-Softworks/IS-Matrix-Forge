from __future__ import annotations

import subprocess
import sys


def test_pixel_grid_entrypoint_imports_without_circular_import():
    """The pixel-grid entry module should import cleanly in a fresh interpreter."""
    result = subprocess.run(
        [
            sys.executable,
            '-c',
            (
                'import importlib; '
                "importlib.import_module('is_matrix_forge.led_matrix.Scripts.pixel_grid')"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
