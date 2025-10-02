import pytest

from is_matrix_forge.led_matrix.constants import WIDTH, HEIGHT
from is_matrix_forge.led_matrix.controller.base import DeviceBase
from is_matrix_forge.led_matrix.controller.components.brightness import manager as brightness_manager_module
from is_matrix_forge.led_matrix.controller.components.brightness.manager import (
    BrightnessManager,
)


class DummyPort:
    device = '/dev/ttyTEST'
    name = 'Test Device'
    serial_number = 'TEST1234'
    location = '1-3.2'


class DummyBrightnessController(BrightnessManager, DeviceBase):
    def __init__(self):
        super().__init__(device=DummyPort(), skip_init_brightness_set=True)


def test_get_brightness_grid_returns_column_major(monkeypatch):
    flat = list(range(WIDTH * HEIGHT))

    monkeypatch.setattr(
        brightness_manager_module,
        '_get_framebuffer_brightness',
        lambda dev: flat,
    )

    controller = DummyBrightnessController()

    grid = controller.get_brightness_grid()

    assert len(grid) == WIDTH
    assert all(len(col) == HEIGHT for col in grid)

    for idx, level in enumerate(flat):
        x = idx % WIDTH
        y = idx // WIDTH
        assert grid[x][y] == level


def test_get_brightness_grid_propagates_errors(monkeypatch):
    def boom(dev):
        raise IOError('bad read')

    monkeypatch.setattr(
        brightness_manager_module,
        '_get_framebuffer_brightness',
        boom,
    )

    controller = DummyBrightnessController()

    with pytest.raises(IOError):
        controller.get_brightness_grid()
