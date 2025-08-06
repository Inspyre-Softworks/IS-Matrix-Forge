import pytest

from is_matrix_forge.led_matrix.display.animations.audio_visualizer import (
    AudioVisualizerAnimation,
)


def test_play_requires_sounddevice():
    vis = AudioVisualizerAnimation()
    with pytest.raises(RuntimeError, match="sounddevice is required"):
        vis.play([])


def test_stop_without_start():
    vis = AudioVisualizerAnimation()
    # should not raise even if not started
    vis.stop()

