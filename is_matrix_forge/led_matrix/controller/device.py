"""Device reference service."""

from __future__ import annotations

from typing import Any, Optional


class DeviceRef:
    """Hold lightweight references to device identity metadata."""

    def __init__(
        self,
        device: Any,
        location: Optional[Any] = None,
        slot: Optional[int] = None,
        side_of_keyboard: Optional[str] = None,
        name: Optional[str] = None,
        serial_number: Optional[str] = None,
    ) -> None:
        self.device = device
        self.location = location if location is not None else getattr(device, 'location', None)
        self.slot = slot if slot is not None else getattr(device, 'slot', None)
        self.side_of_keyboard = (
            side_of_keyboard if side_of_keyboard is not None else getattr(device, 'side_of_keyboard', None)
        )
        self.name = name if name is not None else getattr(device, 'name', None)
        self.serial_number = serial_number if serial_number is not None else getattr(device, 'serial_number', '')

    @property
    def location_abbrev(self) -> Any:
        """Return the abbreviated location if available."""

        if isinstance(self.location, dict):
            return self.location.get('abbrev')
        return self.location

