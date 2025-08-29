"""
Compatibility wrapper for the preset installer.

This module now delegates to the canonical entry point at:
  is_matrix_forge.led_matrix.Scripts.install_presets.main:main

Kept to avoid breaking existing imports or module paths.
"""

from is_matrix_forge.led_matrix.Scripts.install_presets.main import main as _main


def main():  # pragma: no cover - thin wrapper
    _main()


if __name__ == '__main__':  # pragma: no cover
    main()
