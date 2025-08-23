"""Grid management service."""

from __future__ import annotations

from typing import Any, Optional


class GridService:
    """Maintain the grid state and basic drawing helpers."""

    def __init__(self, init_grid: Optional[Any] = None) -> None:
        self.grid = init_grid
        self.last_text: Optional[str] = None
        self.last_percentage: Optional[int] = None

    def clear_matrix(self) -> None:
        self.grid = None

    def draw_grid(self, grid: Optional[Any] = None) -> None:
        if grid is not None:
            self.grid = grid

    def show_text(self, text: str) -> None:
        self.last_text = text

    def draw_percentage(self, percent: int) -> None:
        self.last_percentage = percent

