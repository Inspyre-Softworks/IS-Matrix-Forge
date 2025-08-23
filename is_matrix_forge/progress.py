from __future__ import annotations

"""
Author:
    Inspyre Softworks (Tay-Tay)

Project:
    IS-Matrix-Forge – LED-aware tqdm

File:
    led_tqdm.py

Description:
    tqdm subclass that mirrors progress on an LED matrix and optionally plays
    a completion animation. Supports configurable, parameterized built-in
    animations, custom callables, device round-robin, and a keep-alive
    heartbeat to prevent controller fade-outs.

Classes:
    LEDTqdm:
        A tqdm subclass with LED rendering, completion animations, and keep-alive.

Protocols:
    CompletedAnimation:
        Callable signature for completion animations.

Functions:
    tqdm(iterable=None, *args, **kwargs) -> LEDTqdm:
        Convenience wrapper mirroring tqdm.tqdm.

    register_animation(name: str, fn: CompletedAnimation) -> None:
        Register a new named animation.

Constants:
    _ANI_REGISTRY:
        Global registry of built-in animations.
    _CONTROLLERS:
        Cache of LEDMatrixController instances (one per device).

Dependencies:
    tqdm
    is_matrix_forge.led_matrix.helpers.device.DEVICES
    is_matrix_forge.led_matrix.controller.controller.LEDMatrixController

Example Usage:
    from led_tqdm import tqdm

    for _ in tqdm(range(1_000), total=1_000,
                  completed=('flash', {'flashes': 4, 'on_ms': 120, 'off_ms': 90}),
                  completed_clear=True,
                  keepalive_sec=20.0):
        do_work()
"""

import itertools
import threading
import time
import weakref
from typing import Optional, Any, Iterable, List, Callable, Union, Protocol, Dict, Tuple, cast

from tqdm import tqdm as _tqdm

try:
    from is_matrix_forge.led_matrix.helpers.device import DEVICES
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
except Exception:  # pragma: no cover - dependency issues / optional runtime
    DEVICES = []
    LEDMatrixController = None  # type: ignore[misc,assignment]


# -- Controller cache ---------------------------------------------------------

if 'LEDMatrixController' in globals() and LEDMatrixController is not None:
    _CONTROLLERS: List[Optional[LEDMatrixController]] = [None for _ in range(len(DEVICES))]
else:  # pragma: no cover - when dependencies missing
    _CONTROLLERS = []  # type: ignore[var-annotated]

_DEVICE_INDEXES = itertools.cycle(range(len(DEVICES))) if DEVICES else None


# -- Active bars (weak) -------------------------------------------------------

# WeakSet avoids leaks if a caller forgets to call .close()
_ACTIVE_BARS: 'weakref.WeakSet[LEDTqdm]' = weakref.WeakSet()  # type: ignore[name-defined]


# -- Animation protocol & built-ins ------------------------------------------

class CompletedAnimation(Protocol):
    def __call__(self, ctrl: Any, /, **kwargs: Any) -> None: ...


def _flash_animation(
        ctrl:    Any, *,
        flashes: int = 3,
        on_ms:   int = 150,
        off_ms:  int = 120
) -> None:
    """
    Minimal animation: blink the 100% state a few times.

    Parameters:
        ctrl:
            LEDMatrixController instance.

        flashes:
            Number of times to blink the 100% state. Default: 3.

        on_ms:
            Milliseconds to keep the 100% state on. Default: 150.

        off_ms:
            Milliseconds to keep the 100% state off. Default: 120.
    """
    try:

        for _ in range(max(0, int(flashes))):
            ctrl.draw_percentage(100)
            time.sleep(max(0, on_ms) / 1000.0)
            ctrl.clear()
            time.sleep(max(0, off_ms) / 1000.0)
        ctrl.draw_percentage(100)  # leave on 100%

    except Exception:
        # Swallow hardware errors; progress already completed
        pass


def _pulse_animation(ctrl: Any, *, pulses: int = 4, step_ms: int = 35) -> None:
    """
    Soft 0→100→0 pulses. Relatively cheap and controller-friendly.
    Expects a "draw_percentage" method; falls back to clear on errors.
    """
    try:
        for _ in range(max(0, int(pulses))):
            for p in range(0, 101, 5):
                ctrl.draw_percentage(p)
                time.sleep(max(0, step_ms) / 1000.0)
            for p in range(100, -1, -5):
                ctrl.draw_percentage(p)
                time.sleep(max(0, step_ms) / 1000.0)
        ctrl.draw_percentage(100)
    except Exception:
        try:
            ctrl.clear()
        except Exception:
            pass


_ANI_REGISTRY: Dict[str, CompletedAnimation] = {
    'flash': _flash_animation,
    'pulse': _pulse_animation,
}


def register_animation(name: str, fn: CompletedAnimation) -> None:
    """
    Register a named completion animation.

    Parameters:
        name:
            Registry key. Lowercased; overwrites existing name.
        fn:
            Callable taking (ctrl, **kwargs).
    """
    _ANI_REGISTRY[name.lower()] = fn


# -- LEDTqdm ------------------------------------------------------------------

class LEDTqdm(_tqdm):
    """
    A tqdm subclass that also renders progress on an LED matrix and can play
    a completion animation once the bar reaches total.

    Parameters (new/extended):
        use_led:
            If True, attempt to mirror the progress to an LED device. Default: True.
        matrix:
            Either an existing LEDMatrixController or a device descriptor suitable
            for constructing one. If None, assigns via round-robin across DEVICES.
        completed:
            One of:
              - None or 'none' (no animation)
              - str name of a registered animation (e.g. 'flash', 'pulse')
              - (name, params) tuple where params is a dict passed to the animation
              - Callable[[ctrl], None] custom animation
        completed_async:
            Run animation in a daemon thread. Default: True.
        completed_delay:
            Seconds to wait before starting animation. Default: 0.0.
        completed_clear:
            Clear the matrix when the animation finishes. Default: False.
        keepalive_sec:
            If set (> 0), start a heartbeat thread that periodically re-renders
            the last known percentage (or calls ctrl.ping() if available) to
            prevent controller auto-dimming. Stops on .close().

    Notes:
        - This class intentionally does not override tqdm's internal lock.
        - All controller I/O is protected by a dedicated _led_lock.
        - Exceptions from hardware paths are swallowed; your progress keeps going.
    """

    def __init__(
            self,
            *args: Any,
            use_led: bool = True,
            matrix: Optional[Any] = None,
            completed: Optional[
                Union[str, Tuple[str, Dict[str, Any]], CompletedAnimation]
            ] = None,
            completed_async: bool = True,
            completed_delay: float = 0.0,
            completed_clear: bool = False,
            keepalive_sec: Optional[float] = None,
            **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)

        # Config (flat assignments keep this simple)
        self._led_lock = threading.Lock()
        self._completed = completed
        self._completed_async = bool(completed_async)
        self._completed_delay = float(completed_delay)
        self._completed_clear = bool(completed_clear)
        self._completed_fired = False
        self._keepalive_sec = keepalive_sec if keepalive_sec and keepalive_sec > 0 else None

        # Threads / flags
        self._keepalive_thread: Optional[threading.Thread] = None
        self._stop_keepalive = threading.Event()

        # Controller
        self._matrix = self._init_controller(use_led, matrix)

        self._last_percent = -1
        _ACTIVE_BARS.add(self)

        # Start keepalive if requested
        self._maybe_start_keepalive()

    def _init_controller(self, use_led: bool, matrix: Optional[Any]) -> Optional[Any]:
        ctrl = self._setup_matrix(use_led, matrix)
        if ctrl:
            try:
                ctrl.clear()
            except Exception:
                pass
        return ctrl

    def _setup_matrix(self, use_led: bool, matrix: Optional[Any]) -> Optional[Any]:
        if not use_led:
            return None
        if matrix is not None:
            if LEDMatrixController and isinstance(matrix, LEDMatrixController):
                return matrix
            return self._init_matrix(matrix, 0)
        if _DEVICE_INDEXES is not None:
            return self._get_controller(next(_DEVICE_INDEXES))
        return None

    # -- Controller helpers ---------------------------------------------------

    @staticmethod
    def _get_controller(index: int) -> Optional[Any]:
        if LEDMatrixController is None or index >= len(DEVICES):  # pragma: no cover
            return None
        ctrl = _CONTROLLERS[index]
        if ctrl is None:
            try:
                ctrl = LEDMatrixController(
                    DEVICES[index],
                    100,
                    thread_safe=True,
                    skip_all_init_animations=True,
                )
            except Exception:
                ctrl = None
            _CONTROLLERS[index] = ctrl
        return ctrl

    @classmethod
    def _init_matrix(cls, matrix: Any, index: int) -> Optional[Any]:
        if LEDMatrixController is None:  # pragma: no cover
            return None
        try:
            return LEDMatrixController(matrix, 100)  # type: ignore[arg-type]
        except Exception:
            return None

    # -- Rendering & animations ----------------------------------------------

    def _render_led(self) -> None:
        if not self._matrix or not self.total:
            return
        if self.n > self.total:
            return
        # Round to avoid sticky 99% on certain divisors
        percent = int(round((self.n / self.total) * 100))
        if percent != self._last_percent:
            try:
                self._matrix.draw_percentage(percent)
            except Exception:
                pass
            self._last_percent = percent

    def _maybe_fire_completed(self) -> None:
        if not self._is_complete_and_pending():
            return
        self._completed_fired = True

        def runner() -> None:
            if self._completed_delay > 0:
                time.sleep(self._completed_delay)
            self._invoke_resolved_animation()
            if self._completed_clear:
                self._safe_clear()

        if self._completed_async:
            threading.Thread(target=runner, name='LEDTqdmCompleted', daemon=True).start()
        else:
            runner()

    def _is_complete_and_pending(self) -> bool:
        if self._completed_fired:
            return False
        if not self.total or self.n < self.total:
            return False
        if not self._matrix:
            return False
        if self._completed in (None, 'none'):
            return False
        return True

    def _invoke_resolved_animation(self) -> None:
        try:
            fn, kwargs = self._resolve_animation()
            fn(self._matrix, **kwargs)
        except Exception:
            # swallow hardware/animation faults — progress is already done
            pass

    def _resolve_animation(self) -> tuple[Callable[..., None], dict]:
        comp = self._completed
        if isinstance(comp, tuple) and len(comp) == 2:
            name, params = cast(Tuple[str, Dict[str, Any]], comp)
            fn = _ANI_REGISTRY.get(str(name).lower())
            if fn:
                return fn, dict(params or {})
            return (lambda *_a, **_k: None), {}
        if isinstance(comp, str):
            fn = _ANI_REGISTRY.get(comp.lower())
            if fn:
                return fn, {}
            return (lambda *_a, **_k: None), {}
        if callable(comp):
            return cast(Callable[..., None], comp), {}
        return (lambda *_a, **_k: None), {}

    def _safe_clear(self) -> None:
        try:
            self._matrix.clear()
        except Exception:
            pass

    # -- Keepalive ------------------------------------------------------------

    def _maybe_start_keepalive(self) -> None:
        if not (self._matrix and self._keepalive_sec):
            return

        def _hb() -> None:
            while not self._stop_keepalive.wait(self._keepalive_sec):
                with self._led_lock:
                    try:
                        if self._last_percent >= 0:
                            self._matrix.draw_percentage(self._last_percent)
                        else:
                            getattr(self._matrix, 'ping', lambda: None)()
                    except Exception:
                        pass

        self._keepalive_thread = threading.Thread(
            target=_hb, name='LEDTqdmKeepAlive', daemon=True
        )
        self._keepalive_thread.start()

    # -- tqdm overrides -------------------------------------------------------

    def update(self, n: int = 1) -> None:  # type: ignore[override]
        """
        Update the progress bar and render the LED matrix.

        Parameters:
            n:
                Number of items to add to the progress bar. Default: 1.

        Returns:
            None.
        """
        with self._led_lock:
            super().update(n)
            self._render_led()
            self._maybe_fire_completed()

    def close(self) -> None:
        """
        Close the progress bar and render the LED matrix.

        Returns:
            None
        """
        self._maybe_fire_completed()

        try:
            super().close()
        finally:
            self._stop_keepalive.set()
            th = self._keepalive_thread

            if th and th.is_alive() and not th.daemon:
                th.join(timeout=0.25)

            _ACTIVE_BARS.discard(self)


# -- Public helper ------------------------------------------------------------


def tqdm(
        iterable: Optional[Iterable[Any]] = None,
        *args: Any,
        **kwargs: Any
) -> LEDTqdm:
    """
    Return an LEDTqdm instance mirroring tqdm.tqdm.

    Parameters:
        iterable:
            Iterable for the progress bar. If None, a manual bar is returned.

        *args, **kwargs:
            All tqdm kwargs plus LEDTqdm extras:
            - use_led, matrix, completed, completed_async,
              completed_delay, completed_clear, keepalive_sec

    Returns:
        LEDTqdm instance.
    """
    return LEDTqdm(iterable, *args, **kwargs)
