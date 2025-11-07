"""Helper utilities for composite grid operations.

This module contains small, dependency-free helpers that are shared between
``CompositeGrid`` and the surrounding utility helpers.  Keeping these
functions in their own module prevents circular-import issues between
``base`` and ``utils``.
"""

from __future__ import annotations

from typing import List, Union

from is_matrix_forge.led_matrix.display.grid import Grid

__all__ = ["load_grid", "transpose"]


def transpose(grid: List[List[int]]) -> List[List[int]]:
    """Transpose a two-dimensional list."""

    return [list(col) for col in zip(*grid)]


def load_grid(grid_like: Union[Grid, List[List[int]]]) -> Grid:
    """Normalize *grid_like* into a :class:`~Grid` instance."""

    if isinstance(grid_like, Grid):
        return grid_like

    if not isinstance(grid_like, list):
        raise ValueError(
            f"grid_like must be a list of lists or a Grid, not {type(grid_like)}"
        )

    try:
        return Grid(init_grid=grid_like)
    except ValueError as exc:
        if str(exc).startswith("ValueError: init_grid must be"):
            # Auto-transpose invalid grids to preserve legacy behaviour.
            return Grid(init_grid=transpose(grid_like))
        raise
