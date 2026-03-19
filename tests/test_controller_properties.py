"""Tests for LED matrix controller side and slot helper logic."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional

import pytest


def _install_test_stubs() -> None:
    """Provide lightweight stand-ins for optional runtime dependencies."""

    import sys

    if "is_matrix_forge.common.dirs" not in sys.modules:
        dirs_module = ModuleType("is_matrix_forge.common.dirs")
        dirs_module.APP_DIRS = type("_Dirs", (), {"user_data_path": Path("/tmp/led-matrix")})()
        dirs_module.APP_DIR = dirs_module.APP_DIRS.user_data_path
        dirs_module.PRESETS_DIR = dirs_module.APP_DIR / "presets"
        sys.modules["is_matrix_forge.common.dirs"] = dirs_module

    if "is_matrix_forge.led_matrix.helpers.device" not in sys.modules:
        helpers_module = ModuleType("is_matrix_forge.led_matrix.helpers.device")
        helpers_module.DEVICES = []
        helpers_module.get_devices = lambda *args, **kwargs: []
        sys.modules["is_matrix_forge.led_matrix.helpers.device"] = helpers_module

    if "is_matrix_forge.led_matrix.controller.controller" not in sys.modules:
        controller_module = ModuleType("is_matrix_forge.led_matrix.controller.controller")

        class LEDMatrixController:  # pragma: no cover - type stub for imports
            pass

        controller_module.LEDMatrixController = LEDMatrixController
        sys.modules["is_matrix_forge.led_matrix.controller.controller"] = controller_module


_install_test_stubs()

from is_matrix_forge.led_matrix.Scripts.led_matrix import (
    find_leftmost_matrix,
    find_rightmost_matrix,
    _filter_controllers_by_side,
)
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


def test_mock_controller_defaults() -> None:
    """Controllers without explicit metadata expose deterministic defaults."""

    controller = MockController("1-4.2")
    assert controller.name == "1-4.2"
    assert controller.device_name == "1-4.2"
    assert controller.serial_number == "SN-1-4.2"
    assert controller.device.serial_number == "SN-1-4.2"


def test_mock_controller_explicit_overrides() -> None:
    """Controllers with explicit name and serial_number use the provided values."""

    controller = MockController(
        "1-4.2",
        name="CustomName",
        serial_number="CustomSerial"
    )
    assert controller.name == "CustomName"
    assert controller.device_name == "CustomName"
    assert controller.serial_number == "CustomSerial"
    assert controller.device.serial_number == "CustomSerial"


def test_mock_controller_unknown_location() -> None:
    """Unknown locations raise ValueError to mirror DeviceBase safeguards."""

    with pytest.raises(ValueError, match="Unknown controller location"):
        MockController("9-9.9")


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
            [
                MockController("1-3.2", "R1"),  # right, slot 1
                MockController("1-4.2", "L1"),  # left,  slot 1 – same slot, left wins
            ],
            {"name": "L1", "side": "left", "slot": 1, "location": "1-4.2"},
            id="mixed-sides-identical-slot-left-preferred",
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

    assert_controller_matches(find_leftmost_matrix(controllers), **expected)


def test_find_leftmost_matrix_with_duplicate_slots() -> None:
    """Selecting the leftmost matrix is stable when slot numbers tie."""

    controllers = [
        MockController("1-4.2", "left-first"),
        MockController("1-4.2", "left-second"),
    ]

    result = find_leftmost_matrix(controllers)
    assert result is not None
    assert result.name == "left-first"
    assert result.device_location == "1-4.2"


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
            [
                MockController("1-4.2", "L1"),
                MockController("1-3.2", "R1"),
            ],
            {"name": "R1", "side": "right", "slot": 1, "location": "1-3.2"},
            id="rightmost-preferred-when-same-slot",
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

    assert_controller_matches(find_rightmost_matrix(controllers), **expected)


def test_find_rightmost_matrix_with_duplicate_slots() -> None:
    """Selecting the rightmost matrix is stable when slot numbers tie."""

    controllers = [
        MockController("1-3.3", "right-second"),
        MockController("1-3.3", "right-first"),
    ]

    result = find_rightmost_matrix(controllers)
    assert result is not None
    assert result.name == "right-second"
    assert result.device_location == "1-3.3"


# ---------------------------------------------------------------------------
# _filter_controllers_by_side
# ---------------------------------------------------------------------------

class _MockArgs:
    """Minimal argparse namespace stand-in."""

    def __init__(self, only_left: bool = False, only_right: bool = False) -> None:
        self.only_left = only_left
        self.only_right = only_right


class TestFilterControllersBySide:
    """_filter_controllers_by_side must honour -L/-R and return exactly one controller."""

    def _lr_pair(self) -> list[MockController]:
        """One left + one right controller."""
        return [
            MockController("1-4.2", "L1"),
            MockController("1-3.2", "R1"),
        ]

    def test_no_flag_returns_all_controllers(self) -> None:
        """Without -L/-R every available controller is returned."""
        controllers = self._lr_pair()
        result = _filter_controllers_by_side(controllers, _MockArgs())
        assert len(result) == 2

    def test_only_right_returns_single_rightmost_controller(self) -> None:
        """``-R`` must return exactly ONE controller (the rightmost), not all right-side devices."""
        controllers = [
            MockController("1-4.2", "L1"),
            MockController("1-3.2", "R1"),
            MockController("1-3.3", "R2"),
        ]
        result = _filter_controllers_by_side(controllers, _MockArgs(only_right=True))
        assert len(result) == 1
        assert result[0].name == "R2"

    def test_only_left_returns_single_leftmost_controller(self) -> None:
        """``-L`` must return exactly ONE controller (the leftmost), not all left-side devices."""
        controllers = [
            MockController("1-4.2", "L1"),
            MockController("1-4.3", "L2"),
            MockController("1-3.2", "R1"),
        ]
        result = _filter_controllers_by_side(controllers, _MockArgs(only_left=True))
        assert len(result) == 1
        assert result[0].name == "L1"

    def test_only_right_from_mixed_pair_picks_right(self) -> None:
        """``-R`` on a standard L+R pair selects the right-side matrix."""
        controllers = self._lr_pair()
        result = _filter_controllers_by_side(controllers, _MockArgs(only_right=True))
        assert len(result) == 1
        assert result[0].side_of_keyboard == "right"

    def test_only_left_from_mixed_pair_picks_left(self) -> None:
        """``-L`` on a standard L+R pair selects the left-side matrix."""
        controllers = self._lr_pair()
        result = _filter_controllers_by_side(controllers, _MockArgs(only_left=True))
        assert len(result) == 1
        assert result[0].side_of_keyboard == "left"

    def test_only_right_returns_empty_for_no_controllers(self) -> None:
        """``-R`` with an empty list returns an empty list."""
        result = _filter_controllers_by_side([], _MockArgs(only_right=True))
        assert result == []

    def test_only_left_returns_empty_for_no_controllers(self) -> None:
        """``-L`` with an empty list returns an empty list."""
        result = _filter_controllers_by_side([], _MockArgs(only_left=True))
        assert result == []

    def test_none_cli_args_returns_all_controllers(self) -> None:
        """Passing ``None`` as cli_args returns all controllers unchanged."""
        controllers = self._lr_pair()
        result = _filter_controllers_by_side(controllers, None)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# DIRECTION_MAP correctness
# ---------------------------------------------------------------------------

class TestDirectionMap:
    """The DIRECTION_MAP in scroll_text must map user-visible labels to the
    animation direction string that produces the expected visual motion."""

    def _get_direction_map(self):
        from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments.commands.scroll_text import DIRECTION_MAP
        return DIRECTION_MAP

    def test_up_maps_to_vertical_up(self) -> None:
        """``-d up`` must scroll text upward (vertical_up animation direction)."""
        assert self._get_direction_map()["up"] == "vertical_up"

    def test_down_maps_to_vertical_down(self) -> None:
        """``-d down`` must scroll text downward (vertical_down animation direction)."""
        assert self._get_direction_map()["down"] == "vertical_down"

    def test_h_maps_to_horizontal(self) -> None:
        """``-d h`` must produce a horizontal scroll."""
        assert self._get_direction_map()["h"] == "horizontal"
