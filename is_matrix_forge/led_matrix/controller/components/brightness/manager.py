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
from is_matrix_forge.led_matrix.errors import InvalidBrightnessError
from is_matrix_forge.led_matrix.hardware import (
    brightness as _set_brightness_raw,
    get_framebuffer_brightness as _get_framebuffer_brightness,
    get_brightness as _get_brightness_raw,
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
        """
        flat = _get_framebuffer_brightness(self.device)
        grid = [[0] * MATRIX_HEIGHT for _ in range(MATRIX_WIDTH)]
        for idx, level in enumerate(flat):
            x = idx % MATRIX_WIDTH
            y = idx // MATRIX_WIDTH
            grid[x][y] = level
        return grid

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
