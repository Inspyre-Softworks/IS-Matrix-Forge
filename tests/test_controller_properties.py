"""Tests for LED matrix controller side and slot helper logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import pytest

from is_matrix_forge.led_matrix.constants import SLOT_MAP


@dataclass(frozen=True)
class MockDevice:
    """Emulate the ``ListPortInfo`` attributes accessed by ``DeviceBase``."""

    location: str
    name: str
    serial_number: str


class MockController:
    """Rich controller mock mirroring the ``DeviceBase`` interface used in scripts."""

    def __init__(
        self,
        location: str,
        name: Optional[str] = None,
        serial_number: Optional[str] = None,
    ) -> None:
        if (location_info := SLOT_MAP.get(location)) is None:
            msg = f"Unknown controller location: {location!r}"
            raise ValueError(msg)

        controller_name = name or location
        self._device = MockDevice(
            location=location,
            name=controller_name,
            serial_number=serial_number or f"SN-{controller_name}",
        )
        self._location_info = location_info

    # --- public attributes matching ``LEDMatrixController`` ---
    @property
    def device(self) -> MockDevice:
        return self._device

    @property
    def device_location(self) -> str:
        return self._device.location

    @property
    def name(self) -> str:
        return self._device.name

    @property
    def device_name(self) -> str:
        return self._device.name

    @property
    def serial_number(self) -> str:
        return self._device.serial_number

    # --- derived helpers ---
    @property
    def location(self) -> dict[str, object]:
        return self._location_info

    @property
    def location_abbrev(self) -> str:
        return self._location_info["abbrev"]

    @property
    def side_of_keyboard(self) -> str:
        return self._location_info["side"]

    @property
    def slot(self) -> int:
        return self._location_info["slot"]


def select_leftmost(controllers: Iterable[MockController]) -> Optional[MockController]:
    """Replicate ``find_leftmost_matrix`` selection logic for mock controllers."""

    if left_devices := [c for c in controllers if c.side_of_keyboard == "left"]:
        return min(left_devices, key=lambda controller: controller.slot)
    return min(
        (c for c in controllers if c.side_of_keyboard == "right"),
        key=lambda controller: controller.slot,
        default=None,
    )


def select_rightmost(controllers: Iterable[MockController]) -> Optional[MockController]:
    """Replicate ``find_rightmost_matrix`` selection logic for mock controllers."""

    if right_devices := [c for c in controllers if c.side_of_keyboard == "right"]:
        return max(right_devices, key=lambda controller: controller.slot)
    return max(
        (c for c in controllers if c.side_of_keyboard == "left"),
        key=lambda controller: controller.slot,
        default=None,
    )


def assert_controller_matches(
    controller: Optional[MockController], *, name: Optional[str], side: Optional[str], slot: Optional[int], location: Optional[str]
) -> None:
    """Verify that a controller matches the expected attributes."""

    if name is None:
        assert controller is None
        return
    assert controller is not None
    assert controller.name == name
    assert controller.device_location == location
    assert controller.side_of_keyboard == side
    assert controller.slot == slot
    assert controller.location["side"] == side
    assert controller.location["slot"] == slot
    abbrev_prefix = "L" if side == "left" else "R"
    assert controller.location_abbrev == f"{abbrev_prefix}{slot}"


@pytest.mark.parametrize(
    ("location", "expected_side", "expected_slot", "expected_abbrev"),
    [
        ("1-4.2", "left", 1, "L1"),
        ("1-3.3", "right", 2, "R2"),
    ],
)
def test_side_of_keyboard_and_slot_properties(
    location: str, expected_side: str, expected_slot: int, expected_abbrev: str
) -> None:
    """Controllers expose the expected side and slot based on the slot map."""

    controller = MockController(location)
    assert controller.side_of_keyboard == expected_side
    assert controller.slot == expected_slot
    assert controller.location == SLOT_MAP[location]
    assert controller.location_abbrev == expected_abbrev


@pytest.mark.parametrize(
    "controllers, expected",
    [
        pytest.param(
            [
                MockController("1-4.3", "L2"),
                MockController("1-3.2", "R1"),
                MockController("1-4.2", "L1"),
            ],
            {"name": "L1", "side": "left", "slot": 1, "location": "1-4.2"},
            id="prefers-left-devices",
        ),
        pytest.param(
            [
                MockController("1-3.3", "R2"),
                MockController("1-3.2", "R1"),
            ],
            {"name": "R1", "side": "right", "slot": 1, "location": "1-3.2"},
            id="fallback-to-right-devices",
        ),
        pytest.param(
            [],
            {"name": None, "side": None, "slot": None, "location": None},
            id="no-devices",
        ),
    ],
)
def test_find_leftmost_matrix(controllers: list[MockController], expected: dict[str, Optional[object]]) -> None:
    """Leftmost selection prefers left devices and falls back appropriately."""

    assert_controller_matches(select_leftmost(controllers), **expected)


@pytest.mark.parametrize(
    "controllers, expected",
    [
        pytest.param(
            [
                MockController("1-4.2", "L1"),
                MockController("1-3.2", "R1"),
                MockController("1-3.3", "R2"),
            ],
            {"name": "R2", "side": "right", "slot": 2, "location": "1-3.3"},
            id="prefers-right-devices",
        ),
        pytest.param(
            [
                MockController("1-4.2", "L1"),
                MockController("1-4.3", "L2"),
            ],
            {"name": "L2", "side": "left", "slot": 2, "location": "1-4.3"},
            id="fallback-to-left-devices",
        ),
        pytest.param(
            [],
            {"name": None, "side": None, "slot": None, "location": None},
            id="no-devices",
        ),
    ],
)
def test_find_rightmost_matrix(controllers: list[MockController], expected: dict[str, Optional[object]]) -> None:
    """Rightmost selection prefers right devices and falls back appropriately."""

    assert_controller_matches(select_rightmost(controllers), **expected)
