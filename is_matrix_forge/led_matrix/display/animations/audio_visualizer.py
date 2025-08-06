"""Audio visualizer animation for LED matrix controllers.

This module exposes :class:`AudioVisualizerAnimation`, an ``Animation``
subclass that streams audio data and renders a simple bar style
visualization on one or more LED matrix controllers.  The class can be
handed directly to :meth:`LEDMatrixController.play_animation` to start the
visualizer.

Both ``sounddevice`` and ``soundfile`` are optional dependencies.  If they
are unavailable the animation will raise a ``RuntimeError`` when ``play`` is
called.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable, List, Optional, Union

import numpy as np

try:  # ``sounddevice`` is an optional dependency
    import sounddevice as sd
except Exception:  # pragma: no cover - optional dependency missing
    sd = None  # type: ignore

try:  # ``soundfile`` is also optional
    import soundfile as sf
except Exception:  # pragma: no cover - optional dependency missing
    sf = None  # type: ignore

from is_matrix_forge.led_matrix.display.animations.animation import Animation
from is_matrix_forge.led_matrix.display.animations.frame.base import Frame
from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController


class AudioVisualizerAnimation(Animation):
    """Stream audio data and render a simple bar visualisation."""

    def __init__(
        self,
        controllers: Iterable[LEDMatrixController] | None = None,
        sample_rate: int = 44_100,
        chunk_size: int = 1_024,
        audio_source: Union[str, Path, None] = None,
        loop_file: bool = True,
    ) -> None:
        super().__init__(frame_data=[], loop=True)
        self.controllers: List[LEDMatrixController] = list(controllers or [])
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._stream: Optional[sd.InputStream] = None  # type: ignore[var-annotated]
        self._thread: Optional[threading.Thread] = None
        self._audio_source: Optional[Path] = (
            Path(audio_source) if audio_source else None
        )
        self._loop_file = loop_file

    # ------------------------------------------------------------------ utils --
    def _process_chunk(self, data: np.ndarray) -> None:  # pragma: no cover - real time
        """Render a frame based on ``data`` samples."""
        amplitude = float(np.linalg.norm(data) / len(data))
        bar_height = min(int(amplitude * 34), 34)

        grid = [[0 for _ in range(34)] for _ in range(9)]
        for x in range(9):
            for y in range(bar_height):
                grid[x][33 - y] = 1

        frame = Frame(grid=grid, duration=0.01)

        for ctrl in self.controllers:
            ctrl.draw_grid(frame.grid)

    def _audio_callback(self, indata, frames, time, status) -> None:  # pragma: no cover - real time
        if not self.is_playing:
            return
        self._process_chunk(indata[:, 0])

    def _file_loop(self) -> None:  # pragma: no cover - requires soundfile
        assert sf is not None and self._audio_source is not None
        while self.is_playing:
            with sf.SoundFile(self._audio_source) as f:
                while self.is_playing:
                    data = f.read(self.chunk_size, dtype="float32")
                    if len(data) == 0:
                        break
                    self._process_chunk(data)
            if not self._loop_file:
                break

    # ------------------------------------------------------------------- API --
    def play(
        self,
        devices: Optional[List[LEDMatrixController]] = None,
        skip_clear_screen: bool = False,
    ) -> None:
        if sd is None:  # pragma: no cover - environment without sounddevice
            raise RuntimeError(
                "sounddevice is required for AudioVisualizerAnimation"
            )

        if self.is_playing:
            return

        self.controllers = list(devices or self.controllers)
        self.is_playing = True
        if self._audio_source is not None:
            if sf is None:
                raise RuntimeError("soundfile is required for file playback")
            self._thread = threading.Thread(target=self._file_loop, daemon=True)
            self._thread.start()
        else:
            self._stream = sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
            )
            self._stream.start()

    def stop(self) -> None:
        if not self.is_playing:
            return

        self.is_playing = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None


# Backwards compatibility alias
AudioVisualizer = AudioVisualizerAnimation

__all__ = ["AudioVisualizerAnimation", "AudioVisualizer"]

