"""Background keep-alive service."""

from __future__ import annotations

import threading
from time import sleep


class KeepAliveService:
    """Periodically ping the device while enabled."""

    def __init__(self, enabled: bool = False, interval: float = 50.0) -> None:
        self._enabled = False
        self.interval = interval
        self._thread: threading.Thread | None = None
        self.enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        value = bool(value)
        if value and not self._enabled:
            self._start_thread()
        elif not value and self._enabled:
            self._enabled = False
        self._enabled = value

    def _start_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self._enabled:
            self._ping()
            sleep(self.interval)

    def _ping(self) -> None:  # pragma: no cover - hardware side effect
        """Hook for subclasses to implement device ping."""

