"""Brightness management service."""

from __future__ import annotations

from typing import Optional


class BrightnessService:
    """Normalize and cache brightness levels."""

    DEFAULT = 75

    def __init__(self, default: Optional[int] = None) -> None:
        self._brightness = self._normalize(default if default is not None else self.DEFAULT)

    @property
    def brightness(self) -> int:
        return self._brightness

    def set_brightness(self, value: int) -> int:
        self._brightness = self._normalize(value)
        return self._brightness

    @staticmethod
    def _normalize(value: int) -> int:
        value = int(value)
        if value < 0:
            return 0
        if value > 100:
            return 100
        return value

