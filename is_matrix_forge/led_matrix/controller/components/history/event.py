from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Deque, Literal, Optional


@dataclass(frozen=True, slots=True)
class DisplayEvent:
    """
    Immutable record of a display action.

    Fields:
        ts: UNIX timestamp when the event was committed.
        kind: 'grid' | 'text' | 'pattern' | 'percentage' | 'animation' | 'clear' | 'restore' | 'brightness'
        meta: Lightweight metadata (e.g., {'text': 'HELLO'}).
        grid: Optional snapshot of the grid (list of lists) if available.
    """
    ts: float
    kind: Literal['grid', 'text', 'pattern', 'percentage', 'animation', 'clear', 'restore', 'brightness']
    meta: dict[str, Any]
    grid: Optional[list[list[int]]] = None


__all__ = ['DisplayEvent']
