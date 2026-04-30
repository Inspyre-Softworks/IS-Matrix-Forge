from __future__ import annotations

import pytest

from is_matrix_forge.led_matrix.display.animations.animation import Animation
from is_matrix_forge.led_matrix.display.animations.errors import AnimationFinishedError
from is_matrix_forge.led_matrix.display.animations.frame.base import Frame


class DummyDevice:
    def __init__(self) -> None:
        self.draw_calls = 0
        self.clear_calls = 0

    def draw_grid(self, grid) -> None:
        self.draw_calls += 1

    def clear(self) -> None:
        self.clear_calls += 1


def _install_device_normalizer_stub(monkeypatch) -> None:
    monkeypatch.setattr(
        Animation,
        "_Animation__normalize_devices",
        lambda self, devices: devices if isinstance(devices, list) else [devices],
    )


def test_single_frame_animation_can_play_once_without_raising(monkeypatch) -> None:
    _install_device_normalizer_stub(monkeypatch)
    device = DummyDevice()
    frame = Frame(grid=[[1]], duration=0, width=1, height=1)
    animation = Animation(frame_data=[frame])

    animation.play([device], skip_clear_screen=True)

    assert device.draw_calls == 1
    assert frame.number_of_plays == 1
    assert animation.playback_finished is True


def test_finished_animation_requires_rewind_before_replay(monkeypatch) -> None:
    _install_device_normalizer_stub(monkeypatch)
    device = DummyDevice()
    frames = [
        Frame(grid=[[1]], duration=0, width=1, height=1),
        Frame(grid=[[0]], duration=0, width=1, height=1),
    ]
    animation = Animation(frame_data=frames)

    animation.play([device], skip_clear_screen=True)

    assert animation.playback_finished is True
    assert [frame.number_of_plays for frame in frames] == [1, 1]

    with pytest.raises(AnimationFinishedError, match='Try rewinding the animation first'):
        animation.play([device], skip_clear_screen=True)

    animation.seek(0)
    animation.play([device], skip_clear_screen=True)

    assert [frame.number_of_plays for frame in frames] == [2, 2]
    assert device.draw_calls == 4


def test_rewind_uses_relative_steps(monkeypatch) -> None:
    _install_device_normalizer_stub(monkeypatch)
    frames = [
        Frame(grid=[[1]], duration=0, width=1, height=1),
        Frame(grid=[[0]], duration=0, width=1, height=1),
        Frame(grid=[[1]], duration=0, width=1, height=1),
    ]
    animation = Animation(frame_data=frames)

    animation.seek(2)
    animation.rewind(1)
    assert animation.cursor == 1

    animation.rewind(10)
    assert animation.cursor == 0


def test_fast_forward_uses_relative_steps(monkeypatch) -> None:
    _install_device_normalizer_stub(monkeypatch)
    frames = [
        Frame(grid=[[1]], duration=0, width=1, height=1),
        Frame(grid=[[0]], duration=0, width=1, height=1),
        Frame(grid=[[1]], duration=0, width=1, height=1),
    ]
    animation = Animation(frame_data=frames)

    animation.fast_forward(2)
    assert animation.cursor == 2

    animation.fast_forward(10)
    assert animation.cursor == 2


def test_rewind_without_steps_goes_to_beginning(monkeypatch) -> None:
    _install_device_normalizer_stub(monkeypatch)
    frames = [
        Frame(grid=[[1]], duration=0, width=1, height=1),
        Frame(grid=[[0]], duration=0, width=1, height=1),
        Frame(grid=[[1]], duration=0, width=1, height=1),
    ]
    animation = Animation(frame_data=frames)

    animation.seek(2)
    animation.rewind()
    assert animation.cursor == 0

    animation.seek(2)
    animation.rewind(0)
    assert animation.cursor == 0


def test_fast_forward_without_steps_goes_to_end(monkeypatch) -> None:
    _install_device_normalizer_stub(monkeypatch)
    frames = [
        Frame(grid=[[1]], duration=0, width=1, height=1),
        Frame(grid=[[0]], duration=0, width=1, height=1),
        Frame(grid=[[1]], duration=0, width=1, height=1),
    ]
    animation = Animation(frame_data=frames)

    animation.fast_forward()
    assert animation.cursor == 2

    animation.seek(0)
    animation.fast_forward(0)
    assert animation.cursor == 2


def test_seek_remains_absolute(monkeypatch) -> None:
    _install_device_normalizer_stub(monkeypatch)
    frames = [
        Frame(grid=[[1]], duration=0, width=1, height=1),
        Frame(grid=[[0]], duration=0, width=1, height=1),
        Frame(grid=[[1]], duration=0, width=1, height=1),
    ]
    animation = Animation(frame_data=frames)

    animation.fast_forward(2)
    animation.seek(1)

    assert animation.cursor == 1


def test_rewind_from_finished_state_uses_finished_position(monkeypatch) -> None:
    _install_device_normalizer_stub(monkeypatch)
    device = DummyDevice()
    frames = [
        Frame(grid=[[1]], duration=0, width=1, height=1),
        Frame(grid=[[0]], duration=0, width=1, height=1),
    ]
    animation = Animation(frame_data=frames)

    animation.play([device], skip_clear_screen=True)
    assert animation.playback_finished is True

    animation.rewind(1)

    assert animation.cursor == 1
