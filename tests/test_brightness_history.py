from __future__ import annotations

from is_matrix_forge.led_matrix.controller.components.history.event import (
    DisplayEvent,
)
from is_matrix_forge.led_matrix.controller.components.history.manager import (
    DisplayHistoryManager,
)


class DummyHistoryController(DisplayHistoryManager):
    """History-only controller that captures restored grayscale grids."""

    def __init__(self):
        """Initialize history and restored-grid capture."""
        self.restored_grid = None
        super().__init__()

    def set_brightness_grid_raw(self, grid):
        """Capture a grayscale restoration without using serial hardware."""
        self.restored_grid = [column[:] for column in grid]


def test_go_back_restores_grayscale_framebuffer():
    """History restoration dispatches grayscale events to the raw grid API."""
    controller = DummyHistoryController()
    levels = [[0 for _ in range(34)] for _ in range(9)]
    levels[4][17] = 123
    event = DisplayEvent(
        ts=1.0,
        kind='brightness_grid',
        meta={},
        brightness_grid=levels,
    )
    controller._display_history.append(event)

    restored = controller.go_back()

    assert restored is event
    assert controller.restored_grid == levels
    assert controller.current_display.kind == 'restore'
    assert controller.current_display.brightness_grid == levels
