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


def _raw_grid(fill=0):
    """Return a valid 9×34 raw brightness test grid."""
    return [[fill for _ in range(HEIGHT)] for _ in range(WIDTH)]


def test_set_brightness_grid_raw_updates_defensive_cache(monkeypatch, controller):
    """A committed raw grid establishes defensively copied controller state."""
    recorded = {}
    monkeypatch.setattr(
        brightness_manager_module,
        '_set_framebuffer_brightness_raw',
        lambda dev, grid: recorded.setdefault('grid', grid),
    )
    grid = _raw_grid()
    grid[3][4] = 127

    controller.set_brightness_grid_raw(grid)

    assert recorded['grid'][3][4] == 127
    assert controller.has_pixel_brightness_state is True
    snapshot = controller.pixel_brightness_grid
    snapshot[3][4] = 0
    assert controller.pixel_brightness_grid[3][4] == 127


def test_set_percentage_grid_converts_to_raw(monkeypatch, controller):
    """Percentage framebuffers are converted to native byte values."""
    recorded = {}
    monkeypatch.setattr(
        brightness_manager_module,
        '_set_framebuffer_brightness_raw',
        lambda dev, grid: recorded.setdefault('grid', grid),
    )
    grid = _raw_grid()
    grid[1][2] = 50

    controller.set_brightness_grid(grid)

    assert recorded['grid'][1][2] == brightness_manager_module.percentage_to_value(
        max_value=255,
        percent=50,
    )


def test_single_pixel_update_preserves_neighbors(monkeypatch, controller):
    """A partial update resends known neighbors unchanged."""
    writes = []
    monkeypatch.setattr(
        brightness_manager_module,
        '_set_framebuffer_brightness_raw',
        lambda dev, grid: writes.append([column[:] for column in grid]),
    )
    initial = _raw_grid(10)
    controller.set_brightness_grid_raw(initial)

    controller.set_pixel_brightness_raw(2, 3, 200)

    assert writes[-1][2][3] == 200
    assert writes[-1][2][4] == 10
    assert writes[-1][1][3] == 10


def test_single_pixel_update_fails_when_framebuffer_unknown(monkeypatch, controller):
    """Unknown framebuffer state blocks unsafe partial hardware writes."""
    monkeypatch.setattr(
        brightness_manager_module,
        '_set_framebuffer_brightness_raw',
        lambda *_: pytest.fail('hardware must not be called'),
    )

    with pytest.raises(brightness_manager_module.FramebufferStateUnknownError):
        controller.set_pixel_brightness(0, 0, 50)


def test_failed_framebuffer_write_does_not_update_cache(monkeypatch, controller):
    """Failed transactions leave framebuffer state unknown."""
    def fail(*_):
        raise IOError('partial write')

    monkeypatch.setattr(
        brightness_manager_module,
        '_set_framebuffer_brightness_raw',
        fail,
    )

    with pytest.raises(IOError):
        controller.set_brightness_grid_raw(_raw_grid())

    assert controller.has_pixel_brightness_state is False


def test_binary_grid_sync_and_invalidation(controller):
    """Binary draws map to 0/255 state and firmware output invalidates it."""
    binary = [[0 for _ in range(HEIGHT)] for _ in range(WIDTH)]
    binary[4][5] = 1

    controller._sync_pixel_brightness_from_binary_grid(binary)
    assert controller.get_pixel_brightness_raw(4, 5) == 255
    assert controller.get_pixel_brightness_raw(4, 6) == 0

    controller._invalidate_pixel_brightness_cache()
    assert controller.has_pixel_brightness_state is False


def test_set_brightness_valid(monkeypatch, controller):
    recorded = {}

    def fake_set(_dev, raw):
        recorded['raw'] = raw

    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', fake_set)
    controller.set_brightness(50)

    expected_raw = brightness_manager_module.percentage_to_value(max_value=255, percent=50)
    assert recorded['raw'] == expected_raw
    assert controller.brightness == 50


def test_set_brightness_zero(monkeypatch, controller):
    recorded = {}

    def fake_set(_dev, raw):
        recorded['raw'] = raw

    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', fake_set)
    controller.set_brightness(0)

    expected_raw = brightness_manager_module.percentage_to_value(max_value=255, percent=0)
    assert recorded['raw'] == expected_raw
    assert controller.brightness == 0


def test_set_brightness_hundred(monkeypatch, controller):
    recorded = {}

    def fake_set(_dev, raw):
        recorded['raw'] = raw

    monkeypatch.setattr(brightness_manager_module, '_set_brightness_raw', fake_set)
    controller.set_brightness(100)

    expected_raw = brightness_manager_module.percentage_to_value(max_value=255, percent=100)
    assert recorded['raw'] == expected_raw
    assert controller.brightness == 100


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


def test_fade_to_target_below_range(controller):
    controller.set_brightness(25)
    with pytest.raises(ValueError):
        controller.fade_to(-10, duration=0)


def test_fade_to_target_above_range(controller):
    controller.set_brightness(25)
    with pytest.raises(ValueError):
        controller.fade_to(150, duration=0)
