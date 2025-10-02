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


@pytest.fixture
def controller(monkeypatch):
    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', lambda dev, raw: None)
    return DummyBrightnessController()


def test_get_brightness_grid_returns_column_major(monkeypatch, controller):
    flat = list(range(WIDTH * HEIGHT))

    monkeypatch.setattr(
        brightness_manager_module,
        '_get_framebuffer_brightness',
        lambda dev: flat,
    )

    grid = controller.get_brightness_grid()

    assert len(grid) == WIDTH
    assert all(len(col) == HEIGHT for col in grid)

    for idx, level in enumerate(flat):
        x = idx % WIDTH
        y = idx // WIDTH
        assert grid[x][y] == level


def test_get_brightness_grid_propagates_errors(monkeypatch, controller):
    def boom(dev):
        raise IOError('bad read')

    monkeypatch.setattr(
        brightness_manager_module,
        '_get_framebuffer_brightness',
        boom,
    )

    with pytest.raises(IOError):
        controller.get_brightness_grid()


def test_set_brightness_valid(monkeypatch, controller):
    recorded = {}

    def fake_set(_dev, raw):
        recorded['raw'] = raw

    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', fake_set)
    controller.set_brightness(50)

    expected_raw = brightness_manager_module.percentage_to_value(max_value=255, percent=50)
    assert recorded['raw'] == expected_raw
    assert controller.brightness == 50


def test_set_brightness_invalid(monkeypatch, controller):
    def boom(_dev, _raw):
        raise ValueError('nope')

    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', boom)

    with pytest.raises(brightness_manager_module.InvalidBrightnessError):
        controller.set_brightness(10)


def test_fade_in_zero_duration(monkeypatch, controller):
    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', lambda *_: None)
    controller.set_brightness(0)
    controller.fade_in(duration=0)
    assert controller.brightness == 100


def test_fade_out_zero_duration(monkeypatch, controller):
    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', lambda *_: None)
    controller.set_brightness(100)
    controller.fade_out(duration=0)
    assert controller.brightness == 0


def test_fade_to_zero_duration(monkeypatch, controller):
    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', lambda *_: None)
    controller.set_brightness(25)
    controller.fade_to(80, duration=0)
    assert controller.brightness == 80
