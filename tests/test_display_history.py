from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from is_matrix_forge.led_matrix.controller.components.history import DisplayHistoryManager


class _Logger:
    def debug(self, _message: str) -> None:
        pass


class _DisplayBackend:
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._brightness = 50
        self._grid = None
        self.method_logger = _Logger()

    def draw_grid(self, grid) -> None:
        self._grid = SimpleNamespace(grid=deepcopy(grid))

    def set_brightness(self, value: int, *args, **kwargs) -> None:
        self._brightness = value


class _Controller(DisplayHistoryManager, _DisplayBackend):
    pass


def test_history_starts_without_a_current_event() -> None:
    controller = _Controller()

    assert controller.current_display is None
    assert controller.current_grid is None


def test_resizing_history_preserves_the_most_recent_events() -> None:
    controller = _Controller(history_maxlen=4)
    for value in range(4):
        controller.draw_grid([[value]])

    controller.max_history_len = 2

    assert [event.grid for event in controller.display_history] == [[[2]], [[3]]]


def test_go_back_restores_the_previous_grid_with_one_history_event() -> None:
    controller = _Controller()
    controller.draw_grid([[1]])
    controller.draw_grid([[2]])

    restored = controller.go_back()

    assert restored is not None
    assert restored.grid == [[1]]
    assert controller._grid.grid == [[1]]
    assert [event.kind for event in controller.display_history] == ['grid', 'grid', 'restore']
    assert controller.current_display.meta['steps'] == 1


@pytest.mark.parametrize('value', [0, -1])
def test_history_lengths_must_be_positive(value: int) -> None:
    with pytest.raises(ValueError):
        _Controller(history_maxlen=value)

    controller = _Controller()
    with pytest.raises(ValueError):
        controller.max_history_len = value


def test_go_back_requires_a_positive_step_count() -> None:
    controller = _Controller()

    with pytest.raises(ValueError):
        controller.go_back(0)
