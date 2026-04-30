from __future__ import annotations

import pytest

from is_matrix_forge.led_matrix.controller.base import DeviceBase
from is_matrix_forge.led_matrix.controller.components.drawing import DrawingManager
from is_matrix_forge.led_matrix.controller.components.game import GameManager
from is_matrix_forge.led_matrix.controller.errors import (
    LEDMatrixControllerGameNotRunningError,
    LEDMatrixControllerGameRunningError,
)
from is_matrix_forge.led_matrix.hardware import Game, GameControlVal, GameOfLifeStartParam


class DummyPort:
    device = '/dev/ttyTEST'
    name = 'Test Device'
    serial_number = 'TEST1234'
    location = '1-3.2'


class DummyGameController(GameManager, DrawingManager, DeviceBase):
    def __init__(self):
        super().__init__(device=DummyPort())


@pytest.fixture
def controller():
    return DummyGameController()


def test_start_game_tracks_running_game(monkeypatch, controller):
    sent = []

    def fake_send_command(dev, command, parameters=None, **kwargs):
        sent.append((dev, command, parameters))
        return None

    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        fake_send_command,
    )

    started = controller.start_game(Game.Snake)

    assert started is Game.Snake
    assert controller.game_running is True
    assert controller.running_game is Game.Snake
    assert sent[-1][2] == [Game.Snake]


def test_send_game_control_uses_enum_and_quit_clears_state(monkeypatch, controller):
    sent = []

    def fake_send_command(dev, command, parameters=None, **kwargs):
        sent.append((dev, command, parameters))
        return None

    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        fake_send_command,
    )

    controller.start_game('snake')
    control = controller.send_game_control('left')
    assert control == int(GameControlVal.Left)
    assert controller.game_running is True

    control = controller.send_game_control(GameControlVal.Quit)
    assert control == int(GameControlVal.Quit)
    assert controller.game_running is False
    assert controller.running_game is None
    assert sent[-1][2] == [GameControlVal.Quit]


def test_start_game_supports_additional_game_parameters(monkeypatch, controller):
    sent = []

    def fake_send_command(dev, command, parameters=None, **kwargs):
        sent.append((dev, command, parameters))
        return None

    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        fake_send_command,
    )

    started = controller.start_game(Game.GameOfLife, GameOfLifeStartParam.Glider)

    assert started is Game.GameOfLife
    assert controller.running_game is Game.GameOfLife
    assert sent[-1][2] == [Game.GameOfLife, GameOfLifeStartParam.Glider]


def test_send_game_control_supports_raw_secondary_player_codes(monkeypatch, controller):
    sent = []

    def fake_send_command(dev, command, parameters=None, **kwargs):
        sent.append((dev, command, parameters))
        return None

    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        fake_send_command,
    )

    controller.start_game(Game.Pong)

    assert controller.send_game_control(5) == 5
    assert controller.send_game_control('2right') == 6
    assert sent[-2][2] == [5]
    assert sent[-1][2] == [6]


def test_play_snake_uses_default_keymap(monkeypatch, controller):
    sent = []

    def fake_send_command(dev, command, parameters=None, **kwargs):
        sent.append((dev, command, parameters))
        return None

    keys = iter(['a', 'w', 'q'])

    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        fake_send_command,
    )

    started = controller.play_snake(key_reader=lambda: next(keys))

    assert started is Game.Snake
    assert sent[0][2] == [Game.Snake]
    assert sent[1][2] == [GameControlVal.Left]
    assert sent[2][2] == [GameControlVal.Up]
    assert sent[3][2] == [GameControlVal.Quit]
    assert controller.game_running is False


def test_play_game_loop_supports_custom_keymap(monkeypatch, controller):
    sent = []

    def fake_send_command(dev, command, parameters=None, **kwargs):
        sent.append((dev, command, parameters))
        return None

    keys = iter(['j', 'l', 'x'])

    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        fake_send_command,
    )

    started = controller.play_game_loop(
        Game.Pong,
        keymap={
            'j': 5,
            'l': '2right',
            'x': GameControlVal.Quit,
        },
        key_reader=lambda: next(keys),
    )

    assert started is Game.Pong
    assert sent[0][2] == [Game.Pong]
    assert sent[1][2] == [5]
    assert sent[2][2] == [6]
    assert sent[3][2] == [GameControlVal.Quit]
    assert controller.game_running is False


def test_send_game_control_requires_active_game(monkeypatch, controller):
    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        lambda *args, **kwargs: None,
    )

    with pytest.raises(LEDMatrixControllerGameNotRunningError):
        controller.send_game_control(GameControlVal.Left)


def test_synchronized_display_methods_raise_when_game_running(monkeypatch, controller):
    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        lambda *args, **kwargs: None,
    )

    controller.start_game(Game.Snake)

    with pytest.raises(LEDMatrixControllerGameRunningError):
        controller.clear_grid()


def test_non_synchronized_brightness_write_paths_raise_when_game_running(monkeypatch):
    from is_matrix_forge.led_matrix.controller.components.brightness.manager import BrightnessManager

    class DummyBrightnessController(GameManager, BrightnessManager, DeviceBase):
        def __init__(self):
            super().__init__(device=DummyPort(), skip_init_brightness_set=True)

    controller = DummyBrightnessController()
    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.game.send_command',
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        'is_matrix_forge.led_matrix.controller.components.brightness.manager._set_brightness_raw',
        lambda *args, **kwargs: None,
    )

    controller.start_game(Game.Snake)

    with pytest.raises(LEDMatrixControllerGameRunningError):
        controller.set_brightness(50)
