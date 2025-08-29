# Author: Inspyre Softworks (Taylor)
# Project: IS-Matrix-Forge
# File: brightness_manager.py
#
# Description:
#     BrightnessManager orchestrates brightness changes (set, fade_in,
#     fade_out, fade_to) for LED matrices, delegating the mechanics of
#     easing, step planning, and safety to helper classes.
#
# Functions:
#     (None – class-based by design)
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

from is_matrix_forge.common.helpers import percentage_to_value
from is_matrix_forge.led_matrix.hardware import brightness as _set_brightness_raw
from is_matrix_forge.led_matrix.errors import InvalidBrightnessError
from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized

# Helpers (one class per file)
from is_matrix_forge.led_matrix.controller.components.brightness.helpers import (
    Percent, Easing, FadeSpec as _BaseFadeSpec,
    FadePlanner, Levels, SafeOps,
    BreatherKiller,
)


@dataclass(frozen=True)
class _FadeSpec(_BaseFadeSpec):
    """
    Description:
        Local alias for helper FadeSpec. Kept for type identity within
        the controller package (optional – remove if you don’t care).

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


class BrightnessManager:
    """
    Description:

        High-level brightness controller with fade orchestration. All math,
        easing, and safety concerns are outsourced to helper classes to keep
        complexity low and testability high.

    Parameters:

        default_brightness (Optional[int]):
            : Initial/default brightness percentage [0..100].

        skip_init_brightness_set (bool):
            : If True, do not issue a hardware brightness call on init.

        **kwargs:
            : Passed to cooperative super().__init__ for mixins.

    Properties:

        brightness (int):
            : Current brightness (or default if unset).

    Methods:

        set_brightness:
            : Set absolute brightness [0..100] (int|float|str like '80%').

        fade_in:
            : Fade from current brightness to target (default=default_brightness).

        fade_out:
            : Fade from current brightness to 0, optionally clear when done.

        fade_to:
            : Fade to a target (absolute or relative like '+10', '-25%').

    Raises:

        InvalidBrightnessError:
            : If hardware layer rejects computed raw value.

        ValueError:
            : If percentage normalization fails (out of [0..100]).
    """

    FACTORY_DEFAULT_BRIGHTNESS: int = 75

    # Ergonomics / tuning knobs (override per subclass/instance as needed)
    MAX_STEPS: Optional[int] = None        # e.g., 120 to cap step count
    MIN_STEP_DELAY: Optional[float] = None # e.g., 1/240 to cap update rate
    PERCEPTION_HZ: int = 60                # target perceptual fps for fades

    # Breather integration (cooperative shutdown config)
    BREATHER_STOP_VERBS = ('stop', 'shutdown', 'disable', 'kill', 'cancel')
    BREATHER_FLAGS_OFF  = ('enabled', 'running', 'active')
    BREATHER_THREADS    = ('thread', 'worker', '_thread', '_worker')

    def __init__(
        self,
        *,
        default_brightness: Optional[int] = None,
        skip_init_brightness_set: bool = False,
        **kwargs
    ):
        self._default_brightness = Percent.norm(
            default_brightness if default_brightness is not None
            else self.FACTORY_DEFAULT_BRIGHTNESS
        )
        self._brightness: Optional[int] = None
        self._set_brightness_on_init = not bool(skip_init_brightness_set)

        # Optional user-settable easing – default to linear if not provided
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

    # ---------- Properties ----------

    @property
    def brightness(self) -> int:
        return self._brightness if self._brightness is not None else self._default_brightness

    @brightness.setter
    def brightness(self, new: Union[int, float, str]):
        # Source of truth lives in set_brightness
        self.set_brightness(new)

    # ---------- Public API ----------

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
            Optional[Thread]: worker thread if non_blocking=True, else None
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
            target=Percent.norm(target if target is not None else self._default_brightness),
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
            Optional[Thread]: worker thread if non_blocking=True, else None
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

    def set_brightness(self, brightness: Union[int, float, str]) -> None:
        """
        Parameters:

            brightness (int | float | str):
                : Absolute brightness (strings like '80%' accepted).
        """
        pct = Percent.norm(brightness)
        raw = percentage_to_value(max_value=255, percent=pct)
        try:
            _set_brightness_raw(self.device, raw)
        except ValueError as e:
            raise InvalidBrightnessError(raw) from e
        self._brightness = pct

    # -------------------- Orchestration --------------------

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
            if clear_when_done and int(target) == 0:
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
        start = max(int(getattr(self, 'brightness', 0)), 0)
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

