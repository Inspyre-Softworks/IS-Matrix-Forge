from __future__ import annotations

"""LED matrix aware progress bars."""

from typing import Optional, Any, Iterable, List

from tqdm import tqdm as _tqdm

try:
    from is_matrix_forge.led_matrix.helpers.device import DEVICES
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
except Exception:  # pragma: no cover - dependency issues
    DEVICES = []
    LEDMatrixController = None  # type: ignore

# Global cache of controller instances so multiple bars can share controllers
if 'LEDMatrixController' in globals() and LEDMatrixController is not None:
    _CONTROLLERS: List[Optional[LEDMatrixController]] = [None for _ in range(len(DEVICES))]
else:  # pragma: no cover - when dependencies missing
    _CONTROLLERS = []  # type: ignore[var-annotated]

# Track how many LEDTqdm bars are active to rotate matrices
_ACTIVE_BARS: List['LEDTqdm'] = []


class LEDTqdm(_tqdm):
    """A ``tqdm`` subclass that also renders progress on an LED matrix."""

    def __init__(self, *args: Any, use_led: bool = True, matrix: Optional[Any] = None,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if matrix is None and use_led:
            from is_matrix_forge.led_matrix.controller import get_controllers
            matrix, _ = get_controllers(threaded=True)

        self._matrix = None
        if use_led:
            index = min(len(_ACTIVE_BARS), max(len(DEVICES) - 1, 0))
            self._matrix = self._init_matrix(matrix, index)
            if self._matrix is not None:
                try:
                    self._matrix.clear()
                except Exception:  # pragma: no cover - hardware errors
                    pass

        self._last_percent = -1
        _ACTIVE_BARS.append(self)

    @staticmethod
    def _get_controller(index: int):
        if LEDMatrixController is None or index >= len(DEVICES):  # pragma: no cover - hardware missing
            return None
        ctrl = _CONTROLLERS[index]
        if ctrl is None:
            try:
                ctrl = LEDMatrixController(DEVICES[index], 100)
            except Exception:
                ctrl = None
            _CONTROLLERS[index] = ctrl
        return ctrl

    @classmethod
    def _init_matrix(cls, matrix: Optional[Any], index: int):
        if matrix is not None:
            if LEDMatrixController and isinstance(matrix, LEDMatrixController):
                return matrix
            try:
                return LEDMatrixController(matrix, 100)  # type: ignore
            except Exception:
                return None
        return cls._get_controller(index)

    def _render_led(self) -> None:
        if not self._matrix or not self.total:
            return
        percent = int(self.n / self.total * 100)
        if percent != self._last_percent:
            try:
                self._matrix.draw_percentage(percent)
            except Exception:
                # Ignore hardware errors in progress display
                pass
            self._last_percent = percent

    def update(self, n: int = 1) -> None:  # type: ignore[override]
        super().update(n)
        self._render_led()

    def close(self) -> None:
        super().close()
        if self._matrix is not None:
            try:
                self._matrix.clear()
            except Exception:  # pragma: no cover - hardware errors
                pass
        if self in _ACTIVE_BARS:
            _ACTIVE_BARS.remove(self)


def tqdm(iterable: Optional[Iterable[Any]] = None, *args: Any, **kwargs: Any):
    """Return an :class:`LEDTqdm` instance like ``tqdm.tqdm``."""
    return LEDTqdm(iterable, *args, **kwargs)
