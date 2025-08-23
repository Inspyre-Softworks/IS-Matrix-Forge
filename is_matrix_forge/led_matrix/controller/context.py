"""Context managers used by the controller façade."""

from __future__ import annotations

from time import sleep


class BreatherPauseCtx:
    """Pause the controller's breather effect within a context."""

    def __init__(self, controller) -> None:
        self.controller = controller
        self._was_breathing = False

    def __enter__(self):  # pragma: no cover - trivial
        if getattr(self.controller, 'breathing', False):
            self._was_breathing = True
            self.controller.breathing = False
            sleep(0.05)

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
        if self._was_breathing:
            self.controller.breathing = True

