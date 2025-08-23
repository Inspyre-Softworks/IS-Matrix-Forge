"""Animation control service."""

from __future__ import annotations

from typing import Any, Callable

from .context import BreatherPauseCtx


class AnimationService:
    """Handle simple animation state and helpers."""

    def __init__(self, controller) -> None:
        self.controller = controller
        self._animating = False

    def animate(self, func: Callable, *args, **kwargs):
        with BreatherPauseCtx(self.controller):
            self._animating = True
            try:
                return func(*args, **kwargs)
            finally:
                self._animating = False

    @property
    def animating(self) -> bool:
        return self._animating

    def halt_animation(self) -> None:
        self._animating = False

    def play_animation(self, animation: Any) -> Any:
        self._animating = True
        return animation

    def scroll_text(self, text: str) -> Any:
        return self.controller.grid_service.show_text(text)

    def flash(self, color: Any) -> Any:  # pragma: no cover - effect is visual
        return color

