from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

DisplayEventKind = Literal[
    'grid', 'text', 'pattern', 'percentage', 'animation', 'clear', 'restore',
    'brightness', 'brightness_grid'
]


@dataclass(frozen=True, slots=True)
class DisplayEvent:
    """
    Immutable record of a display action.

    Fields:
        ts: UNIX timestamp when the event was committed.
        kind: Supported display event discriminator, including
            ``brightness_grid`` for per-LED grayscale framebuffers.
        meta: Lightweight metadata (e.g., {'text': 'HELLO'}).
        grid: Optional binary grid snapshot if available.
        brightness_grid: Optional raw 0..255 grayscale framebuffer snapshot.
    """
    ts: float
    kind: DisplayEventKind
    meta: dict[str, Any]
    grid: Optional[list[list[int]]] = None
    brightness_grid: Optional[list[list[int]]] = None


__all__ = ['DisplayEvent', 'DisplayEventKind']
