"""Utilities for the LED matrix package.

This lightweight package initializer avoids importing optional
hardware-dependent modules at import time so that submodules such as the
`Grid` class can be used in isolation (e.g. during unit tests) without
requiring those dependencies.
"""

try:  # pragma: no cover - optional dependency
    from .controller import LEDMatrixController, get_controllers  # noqa:F401
except Exception:  # pragma: no cover
    LEDMatrixController = None  # type: ignore

    def get_controllers(*args, **kwargs):  # type: ignore
        raise RuntimeError("LEDMatrixController is unavailable")

__all__ = ["LEDMatrixController", "get_controllers"]
