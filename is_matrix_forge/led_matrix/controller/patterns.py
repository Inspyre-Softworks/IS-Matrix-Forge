"""Pattern drawing service."""

from __future__ import annotations

from typing import Any


class PatternService:
    """Store and render named LED patterns."""

    def __init__(self) -> None:
        self._patterns: dict[str, Any] = {}
        self._built_in = ['blank']

    def draw_pattern(self, name: str, grid_service) -> None:
        pattern = self._patterns.get(name)
        if pattern is not None:
            grid_service.draw_grid(pattern)

    def list_patterns(self) -> list[str]:
        return list(self._patterns.keys()) + self._built_in

    @property
    def built_in_pattern_names(self) -> list[str]:
        return list(self._built_in)

