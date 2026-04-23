"""Top-level package for IS Matrix Forge.

Keep package imports lightweight so submodules can be imported in isolation
without eagerly initializing the full controller stack.
"""

from __future__ import annotations

__all__ = ["get_controllers"]


def __getattr__(name: str):
    if name == "get_controllers":
        from is_matrix_forge.led_matrix.controller import get_controllers

        globals()["get_controllers"] = get_controllers
        return get_controllers

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
