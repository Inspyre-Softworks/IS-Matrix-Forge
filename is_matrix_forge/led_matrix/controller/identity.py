"""Device identification helpers."""

from __future__ import annotations

from typing import Any

from .device import DeviceRef


class IdentifyService:
    """Provide user-facing identity information."""

    def __init__(self, device_ref: DeviceRef) -> None:
        self.device_ref = device_ref
        self._display_name = device_ref.name or ''
        self._display_location = device_ref.location or ''

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def display_location(self) -> Any:
        return self._display_location

    def identify(self) -> dict[str, Any]:
        return {'name': self.display_name, 'location': self.display_location}

    def greet(self) -> str:
        return f'Hello {self.display_name}'

