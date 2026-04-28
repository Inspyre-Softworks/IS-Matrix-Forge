from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from is_matrix_forge.led_matrix.controller.helpers import find_leftmost, find_rightmost


@dataclass(frozen=True)
class MockDevice:
    location: str
    name: str
    serial_number: str


class ControllerWithMissingLocation:
    def __init__(self, location: str, name: str):
        self.device = MockDevice(
            location=location,
            name=name,
            serial_number=f"SN-{name}",
        )
        self._location = None

    @property
    def location(self):
        return self._location

    @property
    def name(self):
        return self.device.name


def test_find_rightmost_handles_none_location_by_falling_back_to_device_location():
    controllers = [
        ControllerWithMissingLocation("1-4.2", "L1"),
        ControllerWithMissingLocation("1-3.2", "R1"),
    ]

    result = find_rightmost(controllers)

    assert result is not None
    assert result.name == "R1"


def test_find_leftmost_handles_none_location_by_falling_back_to_device_location():
    controllers = [
        ControllerWithMissingLocation("1-4.2", "L1"),
        ControllerWithMissingLocation("1-3.2", "R1"),
    ]

    result = find_leftmost(controllers)

    assert result is not None
    assert result.name == "L1"


def test_find_rightmost_normalizes_windows_style_device_location_suffix():
    controllers = [
        ControllerWithMissingLocation("1-4.2:x.3", "L1"),
        ControllerWithMissingLocation("1-3.3:x.4", "R2"),
    ]

    result = find_rightmost(controllers)

    assert result is not None
    assert result.name == "R2"
