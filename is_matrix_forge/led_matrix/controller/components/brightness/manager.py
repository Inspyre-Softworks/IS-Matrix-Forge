# Author: Inspyre Softworks (Taylor)
# Project: IS-Matrix-Forge
# File: brightness_manager.py
#
# Description:
#     BrightnessManager orchestrates brightness changes (set, fade_in, fade_out, fade_to)
#     for LED matrices, delegating easing/step-planning/safety to helper classes.
#     This version makes I/O contracts explicit:
#       - _read_brightness_raw(): returns 0..255 from hardware (with a tiny retry)
#       - _read_brightness_pct(): returns 0..100 as an int
#     Caching is enabled by default so repeated reads do not hammer hardware
#     on devices that can hang under frequent probes.
#
# Functions:
#     (None — class-based by design)
#
# Constants:
#     FACTORY_DEFAULT_BRIGHTNESS: int
#
# Dependencies:
#     - is_matrix_forge.common.helpers.percentage_to_value
#     - is_matrix_forge.led_matrix.hardware.brightness
#     - is_matrix_forge.led_matrix.errors.InvalidBrightnessError
#     - is_matrix_forge.led_matrix.controller.helpers.threading.synchronized
#     - is_matrix_forge.led_matrix.controller.helpers.brightness.*
#
# Example Usage:
#     manager = BrightnessManager(device=my_device)
#     manager.fade_out(0.5)
#     manager.fade_in(0.5, target=80)
#     manager.fade_to('+10', 0.25, easing=Easing.ease_in_out_cubic)

from __future__ import annotations

from dataclasses import dataclass
from threading import Thread
from time import sleep
from collections.abc import Sequence
from typing import Callable, Optional, Union

from aliaser import alias, Aliases
from is_matrix_forge.common.helpers import percentage_to_value
from is_matrix_forge.led_matrix.constants import WIDTH as MATRIX_WIDTH, HEIGHT as MATRIX_HEIGHT
# Helpers (one class per file)
from is_matrix_forge.led_matrix.controller.components.brightness.helpers import (
    Percent, Easing, FadeSpec as _BaseFadeSpec,
    FadePlanner, Levels, SafeOps,
    BreatherKiller,
)
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
from is_matrix_forge.led_matrix.errors import (
    FramebufferStateUnknownError,
    InvalidBrightnessError,
)
from is_matrix_forge.led_matrix.hardware import (
    brightness as _set_brightness_raw,
    get_framebuffer_brightness as _get_framebuffer_brightness,
    get_brightness as _get_brightness_raw,
    normalize_framebuffer_brightness_grid as _normalize_framebuffer_brightness_grid,
    set_framebuffer_brightness as _set_framebuffer_brightness_raw,
)


# --------------------------------------------------------------------------------------
# Local FadeSpec alias (type identity convenience)
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class _FadeSpec(_BaseFadeSpec):
    """
    Description:
        Local alias for helper FadeSpec. Kept for type identity within the controller
        package (optional — remove if you don’t care).

    Properties:
        start:
            : Starting brightness [0..100].
        target:
            : Target brightness [0..100].
        total_steps:
            : Number of increments for the fade (>=1).
        step_delay:
            : Delay between steps in seconds (>=0).
        clear_when_done:
            : If True and target==0, call clear() at end.
    """
    pass


# --------------------------------------------------------------------------------------
# BrightnessManager
# --------------------------------------------------------------------------------------

class BrightnessManager(Aliases):
    """
    Description:
        High-level brightness controller with fade orchestration. All math, easing,
        and safety concerns are outsourced to helper classes to keep complexity low
        and testability high.

    Parameters:
        default_brightness (Optional[int]):
            : Initial/default brightness percentage [0..100].

        skip_init_brightness_set (bool):
            : If True, do not issue a hardware brightness call on init.

        use_cache (bool):
            : If True (default), cache the last-read percent value and lazily
              refresh it from hardware. If False, read from hardware on every
              access to `brightness`.

        **kwargs:
            : Passed to cooperative super().__init__ for mixins.

    Properties:
        brightness (int):
            : Current brightness [0..100]. If use_cache=False, always reflects hardware.
              If use_cache=True, returns the last cached value (lazily populated).

        actual_brightness (int):
            : Raw device brightness [0..255]. Getter refreshes the percent cache when
              caching is enabled. Setter writes raw and refreshes percent cache.

    Methods:
        set_brightness:
            : Set absolute brightness [0..100] (int|float|str like '80%').

        fade_in:
            : Fade from current brightness to target (default=default_brightness).

        fade_out:
            : Fade from current brightness to 0, optionally clear when done.

        fade_to:
            : Fade to a target (absolute or relative like '+10', '-25%').

        get_brightness_grid:
            : Return a MATRIX_WIDTH x MATRIX_HEIGHT list of per-pixel brightness ints.

        set_brightness_grid / set_brightness_grid_raw:
            : Atomically display a complete percentage or native 0..255 framebuffer.

        set_pixel_brightness / set_pixel_brightness_raw:
            : Safely update one LED after complete framebuffer state is known.

    Raises:
        InvalidBrightnessError:
            : If hardware layer rejects computed raw value.

        ValueError:
            : If percentage normalization fails (out of [0..100]).
    """

    FACTORY_DEFAULT_BRIGHTNESS: int = 75

    # Ergonomics / tuning knobs (override per subclass/instance as needed)
    MAX_STEPS: Optional[int] = None  # e.g., 120 to cap step count
    MIN_STEP_DELAY: Optional[float] = None  # e.g., 1/240 to cap update rate
    PERCEPTION_HZ: int = 60  # target perceptual fps for fades

    # Breather integration (cooperative shutdown config)
    BREATHER_STOP_VERBS = ('stop', 'shutdown', 'disable', 'kill', 'cancel')
    BREATHER_FLAGS_OFF = ('enabled', 'running', 'active')
    BREATHER_THREADS = ('thread', 'worker', '_thread', '_worker')

    # Caching policy — default ON to avoid repeated hardware probes
    USE_CACHE: bool = True

    def __init__(
            self,
            *,
            default_brightness: Optional[int] = None,
            skip_init_brightness_set: bool = False,
            use_cache: Optional[bool] = None,
            **kwargs
    ):
        # defaults
        self._default_brightness = Percent.norm(
            default_brightness if default_brightness is not None
            else self.FACTORY_DEFAULT_BRIGHTNESS
        )
        self._set_brightness_on_init = not skip_init_brightness_set

        # runtime policy
        if use_cache is not None:
            self.USE_CACHE = bool(use_cache)

        # optional cache container (only honored if USE_CACHE=True)
        self._brightness_cache: Optional[int] = None
        # The stock firmware cannot read its grayscale framebuffer. Partial
        # pixel updates are therefore allowed only after this process has
        # established a known complete framebuffer.
        self._pixel_brightness_cache: Optional[list[list[int]]] = None

        # Optional user-settable easing — default to linear if not provided
        # You can override self.easing at runtime with any f:[0,1]->[0,1].
        self.easing: Optional[Callable[[float], float]] = None

        # Helper instances (configurable/override-able)
        self._breather_killer = BreatherKiller(
            stop_verbs=self.BREATHER_STOP_VERBS,
            flags_off=self.BREATHER_FLAGS_OFF,
            worker_attrs=self.BREATHER_THREADS,
        )

        super().__init__(**kwargs)  # cooperative for mixins

        if self._set_brightness_on_init:
            self.set_brightness(self._default_brightness)

    # ----------------------------------------------------------------------------------
    # Hardware I/O — explicit contracts (no ambiguity, no double-conversion)
    # ----------------------------------------------------------------------------------

    @synchronized
    def _read_brightness_raw(self) -> int:
        """
        Returns:
            int: Device-reported brightness [0..255].

        Notes:
            Brief retry smooths over occasional None during USB hiccups/init.
        Raises:
            RuntimeError: If no valid reading is obtained after retries.
        """
        attempts = 3
        for _ in range(attempts):
            raw = _get_brightness_raw(self.device)
            if isinstance(raw, int):
                if 0 <= raw <= 255:
                    return raw
                raise RuntimeError(f'Hardware returned out-of-range brightness: {raw!r}')
            sleep(0.005)
        raise RuntimeError('Could not read brightness from device (got None).')

    def _read_brightness_pct(self) -> int:
        """
        Returns:
            int: Device-reported brightness as percent [0..100], rounded to int.
        """
        raw = self._read_brightness_raw()
        return Percent.from_ratio(raw, 255)

    # ----------------------------------------------------------------------------------
    # Properties — percent/raw views (cache optional)
    # ----------------------------------------------------------------------------------

    @property
    def brightness(self) -> int:
        """
        Returns:
            int: Current brightness percent [0..100].

        Notes:
            - If USE_CACHE=False, always reads from hardware.
            - If USE_CACHE=True, lazily fills cache and returns cached value.
        """
        if not self.USE_CACHE:
            return self._read_brightness_pct()
        return self._ensure_cached_brightness()

    @brightness.setter
    def brightness(self, value) -> None:
        """
        Parameters:
            value (int | float | str):
                : Absolute brightness (e.g., 80, 80.0, '80', '80%').
        """
        self.set_brightness(value)

    @property
    @alias('brightness_raw')
    def actual_brightness(self) -> int:
        """
        Returns:
            int: Raw device brightness [0..255].

        Notes:
            Refreshes the cached percent value from the device-reported value.
        """
        raw = self._read_brightness_raw()
        self._brightness_cache = Percent.from_ratio(raw, 255)
        return raw

    @actual_brightness.setter
    def actual_brightness(self, value: int) -> None:
        """
        Parameters:
            value (int):
                : Raw device brightness [0..255].
        Raises:
            ValueError: If value is out of range.
            InvalidBrightnessError: If hardware rejects the raw write.
        """
        if hasattr(self, '_ensure_game_not_running'):
            self._ensure_game_not_running(method_name='actual_brightness')
        if value < 0:
            raise ValueError(f'Brightness can not go below 0! {value} was provided.')
        if value > 255:
            raise ValueError(f'Brightness can not go above 255! {value} was provided.')
        try:
            _set_brightness_raw(self.device, value)
        finally:
            # keep cache honest even if hardware layer raises after write attempt
            self._brightness_cache = Percent.from_ratio(max(0, min(255, value)), 255)

    # ----------------------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------------------

    def clear_cached_brightness(self) -> None:
        """Forget the cached percent value (only relevant if USE_CACHE=True)."""
        self._brightness_cache = None

    def _ensure_cached_brightness(self) -> int:
        if self._brightness_cache is None:
            self._brightness_cache = self._read_brightness_pct()
        return self._brightness_cache

    @synchronized(pause_breather=False)
    def set_brightness(self, brightness: Union[int, float, str]) -> None:
        """
        Parameters:
            brightness (int | float | str):
                : Absolute brightness (strings like '80%' accepted).

        Raises:
            InvalidBrightnessError: If the hardware rejects the raw value.
            ValueError: If normalization fails.
        """
        pct = Percent.norm(brightness)
        raw = percentage_to_value(max_value=255, percent=pct)
        try:
            _set_brightness_raw(self.device, raw)
        except ValueError as e:
            raise InvalidBrightnessError(raw) from e
        self._brightness_cache = pct

    @synchronized(pause_breather=False)
    def get_brightness_grid(self) -> list[list[int]]:
        """
        Returns:
            list[list[int]]: Per-pixel brightness values as a MATRIX_WIDTH × MATRIX_HEIGHT grid.

        Notes:
            Command 0x0B is supported only by some firmware builds. Stock
            Framework firmware does not currently expose a framebuffer read.
        """
        flat = _get_framebuffer_brightness(self.device)
        grid = [[0] * MATRIX_HEIGHT for _ in range(MATRIX_WIDTH)]
        for idx, level in enumerate(flat):
            x = idx % MATRIX_WIDTH
            y = idx // MATRIX_WIDTH
            grid[x][y] = level
        # A real serial response is byte-valued. Preserve the historical
        # getter contract here rather than adding stricter validation to reads;
        # every write path validates before touching hardware.
        self._pixel_brightness_cache = [column[:] for column in grid]
        return [column[:] for column in grid]

    @property
    def has_pixel_brightness_state(self) -> bool:
        """Whether this controller can safely preserve pixels during partial updates."""
        return self._pixel_brightness_cache is not None

    @property
    def pixel_brightness_grid(self) -> list[list[int]]:
        """Return a defensive copy of the known raw 0..255 framebuffer."""
        return [column[:] for column in self._require_pixel_brightness_cache()]

    def _require_pixel_brightness_cache(self) -> list[list[int]]:
        """Return the known framebuffer or reject an unsafe partial update."""
        if self._pixel_brightness_cache is None:
            raise FramebufferStateUnknownError()
        return self._pixel_brightness_cache

    def _write_pixel_brightness_grid(
        self,
        grid: Sequence[Sequence[int]],
        *,
        operation: str,
        meta: Optional[dict] = None,
    ) -> None:
        """Validate, commit, cache, and record one complete framebuffer."""
        normalized = _normalize_framebuffer_brightness_grid(grid)
        _set_framebuffer_brightness_raw(self.device, normalized)
        # Update state only after the complete transaction and commit succeed.
        self._pixel_brightness_cache = [column[:] for column in normalized]
        self._record_pixel_brightness_event(
            operation=operation,
            grid=normalized,
            meta=meta,
        )

    def _record_pixel_brightness_event(
        self,
        *,
        operation: str,
        grid: list[list[int]],
        meta: Optional[dict] = None,
    ) -> None:
        """Record a grayscale display event when history support is composed in."""
        recorder = getattr(self, '_record_event', None)
        if not callable(recorder):
            return
        event_meta = {'operation': operation, 'unit': 'raw'}
        event_meta.update(meta or {})
        recorder(
            'brightness_grid',
            meta=event_meta,
            brightness_grid=[column[:] for column in grid],
        )

    @staticmethod
    def _validate_pixel_coordinates(x: int, y: int) -> None:
        """Validate one physical matrix coordinate."""
        if isinstance(x, bool) or not isinstance(x, int):
            raise TypeError('x must be an integer')
        if isinstance(y, bool) or not isinstance(y, int):
            raise TypeError('y must be an integer')
        if not 0 <= x < MATRIX_WIDTH:
            raise IndexError(f'x must be between 0 and {MATRIX_WIDTH - 1}')
        if not 0 <= y < MATRIX_HEIGHT:
            raise IndexError(f'y must be between 0 and {MATRIX_HEIGHT - 1}')

    @synchronized
    def set_brightness_grid_raw(self, grid: Sequence[Sequence[int]]) -> None:
        """Display a complete column-major 9×34 grid of raw 0..255 levels."""
        self._write_pixel_brightness_grid(grid, operation='set_grid_raw')

    @synchronized
    def set_brightness_grid(self, grid: Sequence[Sequence[Union[int, float, str]]]) -> None:
        """Display a complete column-major 9×34 grid of percentage levels."""
        if isinstance(grid, (str, bytes, bytearray)) or not isinstance(grid, Sequence):
            raise TypeError('brightness grid must be a sequence of columns')
        if len(grid) != MATRIX_WIDTH:
            raise ValueError(f'brightness grid must contain exactly {MATRIX_WIDTH} columns')

        raw_grid: list[list[int]] = []
        for x, column in enumerate(grid):
            if isinstance(column, (str, bytes, bytearray)) or not isinstance(column, Sequence):
                raise TypeError(f'brightness column {x} must be a sequence')
            if len(column) != MATRIX_HEIGHT:
                raise ValueError(
                    f'brightness column {x} must contain exactly {MATRIX_HEIGHT} values'
                )
            raw_column = []
            for y, value in enumerate(column):
                if isinstance(value, bool):
                    raise TypeError(f'brightness at ({x}, {y}) cannot be a boolean')
                pct = Percent.norm(value)
                raw_column.append(percentage_to_value(max_value=255, percent=pct))
            raw_grid.append(raw_column)

        self._write_pixel_brightness_grid(
            raw_grid,
            operation='set_grid_percent',
            meta={'input_unit': 'percent'},
        )

    @synchronized
    def set_pixel_brightness_raw(self, x: int, y: int, value: int) -> None:
        """Set one LED to a raw 0..255 level while preserving known neighbors."""
        self._validate_pixel_coordinates(x, y)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError('raw pixel brightness must be an integer')
        if not 0 <= value <= 255:
            raise ValueError('raw pixel brightness must be between 0 and 255')

        grid = [column[:] for column in self._require_pixel_brightness_cache()]
        grid[x][y] = value
        self._write_pixel_brightness_grid(
            grid,
            operation='set_pixel_raw',
            meta={'x': x, 'y': y, 'value': value},
        )

    @synchronized
    def set_pixel_brightness(
        self,
        x: int,
        y: int,
        brightness: Union[int, float, str],
    ) -> None:
        """Set one LED using a 0..100 percentage while preserving known neighbors."""
        self._validate_pixel_coordinates(x, y)
        if isinstance(brightness, bool):
            raise TypeError('pixel brightness cannot be a boolean')
        pct = Percent.norm(brightness)
        raw = percentage_to_value(max_value=255, percent=pct)

        grid = [column[:] for column in self._require_pixel_brightness_cache()]
        grid[x][y] = raw
        self._write_pixel_brightness_grid(
            grid,
            operation='set_pixel_percent',
            meta={'x': x, 'y': y, 'value': pct, 'input_unit': 'percent'},
        )

    def get_pixel_brightness_raw(self, x: int, y: int) -> int:
        """Return one known raw 0..255 pixel level without probing firmware."""
        self._validate_pixel_coordinates(x, y)
        return self._require_pixel_brightness_cache()[x][y]

    def get_pixel_brightness(self, x: int, y: int) -> int:
        """Return one known pixel level as a rounded 0..100 percentage."""
        return Percent.from_ratio(self.get_pixel_brightness_raw(x, y), 255)

    def _sync_pixel_brightness_from_binary_grid(
        self,
        grid: Sequence[Sequence[int]],
    ) -> None:
        """Track a binary drawing operation as a raw 0/255 framebuffer."""
        raw = [[0] * MATRIX_HEIGHT for _ in range(MATRIX_WIDTH)]
        for x in range(min(len(grid), MATRIX_WIDTH)):
            column = grid[x]
            for y in range(min(len(column), MATRIX_HEIGHT)):
                raw[x][y] = 255 if column[y] else 0
        self._pixel_brightness_cache = raw

    def _invalidate_pixel_brightness_cache(self) -> None:
        """Forget framebuffer state after a firmware-rendered display operation."""
        self._pixel_brightness_cache = None

    # ----------------------------------------------------------------------------------
    # Fade orchestration
    # ----------------------------------------------------------------------------------

    @synchronized(pause_breather=False)
    def fade_out(
            self,
            duration: float = 0.33,
            *,
            clear_when_done: bool = False,
            non_blocking: bool = False,
            steps: Optional[int] = None,
            easing: Optional[Callable[[float], float]] = None,
    ) -> Optional[Thread]:
        """
        Parameters:
            duration (float):
                : Total fade time in seconds. Defaults to 0.33.
            clear_when_done (bool):
                : If True, call clear() after fade if target is 0.
            non_blocking (bool):
                : If True, run on a daemon thread and return it.
            steps (Optional[int]):
                : Explicit number of steps; if None, computed from fps and delta.
            easing (Optional[Callable[[float], float]]):
                : Easing function f:[0,1]->[0,1]. Defaults to self.easing or linear.

        Returns:
            Optional[Thread]: Worker thread if non_blocking=True, else None.
        """
        self._kill_breather()
        return self._fade(
            target=0,
            duration=duration,
            clear_when_done=clear_when_done,
            non_blocking=non_blocking,
            steps=steps,
            easing=easing,
        )

    @synchronized(pause_breather=False)
    def fade_in(
            self,
            duration: float = 0.33,
            *,
            target: Optional[int] = None,
            non_blocking: bool = False,
            steps: Optional[int] = None,
            easing: Optional[Callable[[float], float]] = None,
    ) -> Optional[Thread]:
        """
        Parameters:
            duration (float):
                : Total fade time in seconds.
            target (Optional[int]):
                : Destination brightness [0..100]. Defaults to default_brightness.
            non_blocking (bool):
                : If True, run on a daemon thread and return it.
            steps (Optional[int]):
                : Explicit number of steps; if None, computed from fps and delta.
            easing (Optional[Callable[[float], float]]):
                : Easing function f:[0,1]->[0,1]. Defaults to self.easing or linear.
        """
        self._kill_breather()
        return self._fade(
            target=Percent.norm(target if target is not None else 100),
            duration=duration,
            clear_when_done=False,
            non_blocking=non_blocking,
            steps=steps,
            easing=easing,
        )

    @synchronized(pause_breather=False)
    def fade_to(
            self,
            target: Union[int, float, str],
            duration: float = 0.33,
            *,
            non_blocking: bool = False,
            steps: Optional[int] = None,
            easing: Optional[Callable[[float], float]] = None,
            clear_when_done: Optional[bool] = None,
    ) -> Optional[Thread]:
        """
        Parameters:
            target (int | float | str):
                : Destination brightness in [0..100], or relative like '+10', '-25%'.
            duration (float):
                : Total fade time in seconds. Defaults to 0.33.
            non_blocking (bool):
                : If True, run the fade on a daemon thread and return it.
            steps (Optional[int]):
                : Explicit number of steps; if None, computed from fps and delta.
            easing (Optional[Callable[[float], float]]):
                : Easing function f:[0,1]->[0,1]. Defaults to self.easing or linear.
            clear_when_done (Optional[bool]):
                : If None, auto-clear only when final target == 0. Otherwise obey.

        Returns:
            Optional[Thread]: Worker thread if non_blocking=True, else None.
        """
        self._kill_breather()
        tgt = self._resolve_target(target)
        do_clear = (clear_when_done if clear_when_done is not None else (tgt == 0))
        return self._fade(
            target=tgt,
            duration=duration,
            clear_when_done=do_clear,
            non_blocking=non_blocking,
            steps=steps,
            easing=easing,
        )

    # -------------------- Orchestration internals --------------------

    def _fade(
            self,
            *,
            target: int,
            duration: float,
            clear_when_done: bool,
            non_blocking: bool,
            steps: Optional[int],
            easing: Optional[Callable[[float], float]],
    ) -> Optional[Thread]:
        # Zero-duration fast path
        if duration <= 0:
            self.set_brightness(Percent.norm(target))
            if clear_when_done and target == 0:
                SafeOps.clear(self)
            return None

        spec = self._make_fade_spec(
            target=target,
            duration=duration,
            steps=steps,
            easing=easing,
            clear_when_done=clear_when_done,
        )

        if spec.start == spec.target:
            if spec.clear_when_done and spec.target == 0:
                SafeOps.clear(self)
            return None

        return self._execute_fade(spec, non_blocking)

    def _make_fade_spec(
            self,
            *,
            target: int,
            duration: float,
            steps: Optional[int],
            easing: Optional[Callable[[float], float]],
            clear_when_done: bool,
    ) -> _FadeSpec:
        # Read current brightness as percent; no cache by default
        start = max(int(self.brightness), 0)
        tgt = Percent.norm(target)

        base_spec = FadePlanner.make_spec(
            start=start,
            target=tgt,
            duration=duration,
            fps=self.PERCEPTION_HZ,
            steps=steps,
            max_steps=self.MAX_STEPS,
            min_step_delay=self.MIN_STEP_DELAY,
            clear_when_done=clear_when_done,
        )
        # local type alias instance
        return _FadeSpec(**base_spec.__dict__)

    def _execute_fade(self, spec: _FadeSpec, non_blocking: bool) -> Optional[Thread]:
        if non_blocking:
            t = Thread(target=self._run_fade, args=(spec,), name='LED-Fade', daemon=True)
            t.start()
            return t
        self._run_fade(spec)
        return None

    def _run_fade(self, spec: _FadeSpec) -> None:
        last = None
        easing_fn = self.easing or Easing.linear
        for level in Levels.iter(spec, easing=easing_fn):
            if level != last:
                self.set_brightness(level)
                last = level
            if spec.step_delay > 0:
                sleep(spec.step_delay)
        if self.brightness != spec.target:
            self.set_brightness(spec.target)
        if spec.clear_when_done and spec.target == 0:
            SafeOps.clear(self)

    # ---------- Breather + targets ----------

    def _kill_breather(self) -> None:
        self._breather_killer.kill(self)

    def _resolve_target(self, target: Union[int, float, str]) -> int:
        """
        Description:
            Resolve absolute or relative targets to a clamped integer percent [0,100].

        Notes:
            - Relative values are applied to current self.brightness.
            - Accepts '+10', '-15', '+10%', '-5%', or absolute like '80%'.
        """
        return Percent.resolve(target, current=self.brightness)
