from __future__ import annotations

from pathlib import Path

import pytest

from is_matrix_forge.led_matrix.display.animations import audio_visualizer as module


class _Thread:
    def __init__(self, *, target, daemon: bool) -> None:
        self.target = target
        self.daemon = daemon
        self.started = False

    def start(self) -> None:
        self.started = True


def test_file_playback_does_not_require_sounddevice(monkeypatch) -> None:
    monkeypatch.setattr(module, 'sd', None)
    monkeypatch.setattr(module, 'sf', object())
    monkeypatch.setattr(module.threading, 'Thread', _Thread)
    visualizer = module.AudioVisualizer([], audio_source=Path('track.wav'))

    visualizer.start()

    assert visualizer._running is True
    assert visualizer._thread is not None
    assert visualizer._thread.started is True


def test_microphone_input_reports_the_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr(module, 'sd', None)
    visualizer = module.AudioVisualizer([])

    with pytest.raises(RuntimeError, match='sounddevice.*microphone'):
        visualizer.start()

    assert visualizer._running is False
