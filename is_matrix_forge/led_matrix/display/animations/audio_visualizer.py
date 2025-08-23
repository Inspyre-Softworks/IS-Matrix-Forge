"""Real-time audio visualizer for the LED matrix.

This module provides a small utility that streams audio data and renders simple
bar style visualizations on one or more LED matrix controllers.  By default it
uses the system microphone for input, however an audio file may also be used as
the source allowing "regular" audio to be visualized.  ``sounddevice`` and
``soundfile`` are optional dependencies and the visualiser gracefully degrades
if they are unavailable.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable, List, Optional, Union

import numpy as np

try:  # ``sounddevice`` is an optional dependency
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional dependency missing
    sd = None  # type: ignore

try:  # ``soundfile`` is also optional
    import soundfile as sf
except ImportError:  # pragma: no cover - optional dependency missing
    sf = None  # type: ignore

from is_matrix_forge.led_matrix.controller import LEDMatrixController
from is_matrix_forge.led_matrix.display.animations.frame.base import Frame


class AudioVisualizer:
    """Stream audio data and render a simple bar visualisation."""

    def __init__(
        self,
        controllers: Iterable[LEDMatrixController],
        sample_rate: int = 44_100,
        chunk_size: int = 1_024,
        audio_source: Union[str, Path, None] = None,
        loop_file: bool = True,
    ) -> None:
        self.controllers: List[LEDMatrixController] = list(controllers)
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._stream: Optional[sd.InputStream] = None  # type: ignore[var-annotated]
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._audio_source: Optional[Path] = Path(audio_source) if audio_source else None
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
        if not self._running:
            return
        self._process_chunk(indata[:, 0])

    def _file_loop(self) -> None:  # pragma: no cover - requires soundfile
        assert sf is not None and self._audio_source is not None
        while self._running:
            with sf.SoundFile(self._audio_source) as f:
                while self._running:
                    data = f.read(self.chunk_size, dtype='float32')
                    if len(data) == 0:
                        break
                    self._process_chunk(data)
            if not self._loop_file:
                break

    # ------------------------------------------------------------------- API --
    def start(self) -> None:
        if sd is None:  # pragma: no cover - environment without sounddevice
            raise RuntimeError("sounddevice is required for AudioVisualizer")

        if self._running:
            return

        self._running = True
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
        if not self._running:
            return

        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None


__all__ = ["AudioVisualizer"]

