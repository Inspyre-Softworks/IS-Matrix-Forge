from .manager import BrightnessManager





# from __future__ import annotations
# from dataclasses import dataclass
# from threading import Thread
# from time import sleep
# from typing import Callable, Optional, Union
#
# from is_matrix_forge.common.helpers import percentage_to_value
# from is_matrix_forge.led_matrix.hardware import brightness as _set_brightness_raw
# from is_matrix_forge.led_matrix.errors import InvalidBrightnessError
# from is_matrix_forge.led_matrix.controller.helpers.threading import synchronized
#
#
# @dataclass(frozen=True)
# class _FadeSpec:
#     start: int
#     target: int
#     total_steps: int
#     step_delay: float
#     easing: Callable[[float], float]
#     clear_when_done: bool
#
#
# class BrightnessManager:
#     FACTORY_DEFAULT_BRIGHTNESS = 75
#
#     # Optional ergonomics caps (override per class/instance if desired)
#     MAX_STEPS: Optional[int] = None         # e.g., 120
#
#     MAX_STEPS: Optional[int] = None  # leave None; we compute from fps
#     MIN_STEP_DELAY: Optional[float] = 1 / 120  # ~8.33ms (avoid “instant blur”)
#     PERCEPTION_HZ: int = 60  # target visual update rate
#
#     MIN_STEP_DELAY: Optional[float] = None  # e.g., 1/240
#
#     # Breather integration (data-driven to keep complexity tiny)
#     BREATHER_STOP_VERBS = ('stop', 'shutdown', 'disable', 'kill', 'cancel')
#     BREATHER_FLAGS_OFF  = ('enabled', 'running', 'active')
#     BREATHER_THREADS    = ('thread', 'worker', '_thread', '_worker')
#
#     def __init__(self, *, default_brightness: Optional[int] = None,
#                  skip_init_brightness_set: bool = False, **kwargs):
#         self._default_brightness = self._norm_pct(
#             default_brightness if default_brightness is not None
#             else self.FACTORY_DEFAULT_BRIGHTNESS
#         )
#         self._brightness: Optional[int] = None
#         self._set_brightness_on_init = not bool(skip_init_brightness_set)
#         super().__init__(**kwargs)
#         if self._set_brightness_on_init:
#             self.set_brightness(self._default_brightness)
#
#     # ---------- Properties ----------
#
#     @property
#     def brightness(self) -> int:
#         return self._brightness if self._brightness is not None else self._default_brightness
#
#     @brightness.setter
#     def brightness(self, new: Union[int, float, str]):
#         # Source of truth lives in set_brightness; avoid double-assign/normalize
#         self.set_brightness(new)
#
#     # ---------- Public API ----------
#
#     @synchronized(pause_breather=False)
#     def fade_out(self, duration: float = 0.33, *, clear_when_done: bool = False,
#                  non_blocking: bool = False, steps: Optional[int] = None,
#                  easing: Optional[Callable[[float], float]] = None) -> Optional[Thread]:
#         self._kill_breather()
#         return self._fade(
#             target=0,
#             duration=duration,
#             clear_when_done=clear_when_done,
#             non_blocking=non_blocking,
#             steps=steps,
#             easing=easing,
#         )
#
#     @synchronized(pause_breather=False)
#     def fade_in(self, duration: float = 0.33, *, target: Optional[int] = None,
#                 non_blocking: bool = False, steps: Optional[int] = None,
#                 easing: Optional[Callable[[float], float]] = None) -> Optional[Thread]:
#         self._kill_breather()
#         return self._fade(
#             target=self._norm_pct(target if target is not None else self._default_brightness),
#             duration=duration,
#             clear_when_done=False,
#             non_blocking=non_blocking,
#             steps=steps,
#             easing=easing,
#         )
#
#     @synchronized(pause_breather=False)
#     def fade_to(
#             self,
#             target: Union[int, float, str],
#             duration: float = 0.33,
#             *,
#             non_blocking: bool = False,
#             steps: Optional[int] = None,
#             easing: Optional[Callable[[float], float]] = None,
#             clear_when_done: Optional[bool] = None
#     ) -> Optional[Thread]:
#         """
#         Fade brightness from the current level to a target level.
#
#         Parameters:
#             target (int | float | str):
#                 Destination brightness percentage in [0, 100].
#                 Also accepts strings like '80%' or relative values '+10', '-25'.
#
#             duration (float):
#                 Total fade time in seconds. Defaults to 0.33.
#
#             non_blocking (bool):
#                 If True, run the fade on a daemon thread and return it.
#
#             steps (Optional[int]):
#                 Explicit number of steps. If None, computed via PERCEPTION_HZ and delta.
#
#             easing (Optional[Callable[[float], float]]):
#                 Easing function f: [0,1] -> [0,1]. Defaults to linear.
#
#             clear_when_done (Optional[bool]):
#                 If None, will auto-clear only when target resolves to 0.
#                 Otherwise, obey the provided boolean.
#
#         Returns:
#             Optional[Thread]: The worker thread if non_blocking=True, else None.
#         """
#         self._kill_breather()
#         tgt = self._resolve_target(target)
#         do_clear = (clear_when_done if clear_when_done is not None else (tgt == 0))
#         return self._fade(
#             target=tgt,
#             duration=duration,
#             clear_when_done=do_clear,
#             non_blocking=non_blocking,
#             steps=steps,
#             easing=easing,
#         )
#
#     def set_brightness(self, brightness: Union[int, float, str]) -> None:
#         pct = self._norm_pct(brightness)
#         raw = percentage_to_value(max_value=255, percent=pct)
#         try:
#             _set_brightness_raw(self.device, raw)
#         except ValueError as e:
#             raise InvalidBrightnessError(raw) from e
#         self._brightness = pct
#
#     # -------------------- Low-complexity fade orchestration --------------------
#
#     def _fade(self, *, target: int, duration: float,
#               clear_when_done: bool, non_blocking: bool,
#               steps: Optional[int], easing: Optional[Callable[[float], float]]) -> Optional[Thread]:
#
#         # Zero-duration fast path: jump-cut to target
#         if duration <= 0:
#             self.set_brightness(self._norm_pct(target))
#             if clear_when_done and int(target) == 0:
#                 self._safe_clear()
#             return None
#
#         spec = self._make_fade_spec(
#             target=target,
#             duration=duration,
#             steps=steps,
#             easing=easing,
#             clear_when_done=clear_when_done,
#         )
#
#         if self._is_noop(spec):
#             self._maybe_clear_after_noop(spec)
#             return None
#
#         return self._execute_fade(spec, non_blocking)
#
#     # -------------------- Tiny helpers (keep cyclomatic low) --------------------
#
#     def _make_fade_spec(self, *, target: int, duration: float,
#                         steps: Optional[int],
#                         easing: Optional[Callable[[float], float]],
#                         clear_when_done: bool) -> _FadeSpec:
#         start = max(int(getattr(self, 'brightness', 0)), 0)
#         tgt = self._norm_pct(target)
#
#         # 1) base steps on caller OR compute from perceptual fps
#         total = self._calc_steps(start, tgt, steps, duration, self.PERCEPTION_HZ)
#
#         # 2) optional hard cap still supported
#         if self.MAX_STEPS:
#             total = min(total, self.MAX_STEPS)
#
#         # 3) compute delay and clamp to minimum
#         delay = (duration / total) if duration > 0 else 0.0
#         if self.MIN_STEP_DELAY:
#             delay = max(delay, self.MIN_STEP_DELAY)
#
#         ease = easing if easing is not None else self._linear
#         return _FadeSpec(start=start, target=tgt, total_steps=total,
#                          step_delay=delay, easing=ease,
#                          clear_when_done=clear_when_done)
#
#     @staticmethod
#     def _calc_steps(start: int, target: int, steps: Optional[int],
#                     duration: float, fps: int) -> int:
#         if steps and steps > 0:
#             return steps
#         # Compute perceptual steps (duration * fps), never less than delta=1, never 0
#         delta = abs(target - start)
#         perceptual = max(1, int(round(duration * fps)))
#         # Use the *smaller* of delta and perceptual steps to avoid micro-steps
#         return max(1, min(delta, perceptual))
#
#     @staticmethod
#     def _is_noop(spec: _FadeSpec) -> bool:
#         return spec.start == spec.target
#
#     # ---------- Breather kill (low complexity, data-driven) ----------
#
#     def _kill_breather(self) -> None:
#         b = getattr(self, 'breather', None)
#         if not b:
#             return
#         self._breather_stop_verbs(b, self.BREATHER_STOP_VERBS)
#         self._breather_force_flags(b, self.BREATHER_FLAGS_OFF)
#         self._breather_join_workers(b, self.BREATHER_THREADS, timeout=0.1)
#
#     @staticmethod
#     def _breather_stop_verbs(breather, verbs: tuple[str, ...]) -> None:
#         for name in verbs:
#             BrightnessManager._safe_call(getattr(breather, name, None))
#
#     @staticmethod
#     def _breather_force_flags(breather, flags: tuple[str, ...]) -> None:
#         for flag in flags:
#             if hasattr(breather, flag):
#                 BrightnessManager._safe_setattr(breather, flag, False)
#
#     @staticmethod
#     def _breather_join_workers(breather, attrs: tuple[str, ...], *, timeout: float) -> None:
#         for attr in attrs:
#             t = getattr(breather, attr, None)
#             if t is not None and getattr(t, 'is_alive', None):
#                 BrightnessManager._safe_join(t, timeout=timeout)
#
#     # ---------- Execution ----------
#
#     def _maybe_clear_after_noop(self, spec: _FadeSpec) -> None:
#         # Only meaningful for fade-out-to-zero semantics
#         if spec.clear_when_done and spec.target == 0:
#             self._safe_clear()
#
#     def _execute_fade(self, spec: _FadeSpec, non_blocking: bool) -> Optional[Thread]:
#         if non_blocking:
#             t = Thread(target=self._run_fade, args=(spec,), name='LED-Fade', daemon=True)
#             t.start()
#             return t
#         self._run_fade(spec)
#         return None
#
#     def _resolve_target(self, target: Union[int, float, str]) -> int:
#         """
#         Resolve absolute or relative targets to a clamped integer percent [0,100].
#
#         Accepted forms:
#           - 75            -> 75
#           - 75.0          -> 75
#           - '80%'         -> 80
#           - '+10'/'-15'   -> relative to current brightness (in percent points)
#           - '+10%'/'-5%'  -> relative percent points (same as above; '%' optional)
#
#         Notes:
#           - Relative values are applied to current self.brightness.
#           - Final value is clamped to [0, 100].
#         """
#         if isinstance(target, str):
#             s = target.strip()
#             # Relative?
#             if s.startswith(('+', '-')):
#                 sign = 1 if s[0] == '+' else -1
#                 num = s[1:].strip()
#                 if num.endswith('%'):
#                     num = num[:-1].strip()
#                 try:
#                     delta = float(num)
#                 except ValueError:
#                     # fall back to absolute parse if weird input
#                     return self._norm_pct(s)
#                 base = float(self.brightness)
#                 return max(0, min(100, int(round(base + sign * delta))))
#             # Absolute string (may include '%')
#             return self._norm_pct(s)
#         # Numeric absolute
#         return self._norm_pct(target)
#
#     def _run_fade(self, spec: _FadeSpec) -> None:
#         last = None
#         for level in self._levels(spec):
#             if level != last:
#                 self.set_brightness(level)
#                 last = level
#             if spec.step_delay > 0:
#                 sleep(spec.step_delay)
#         if self.brightness != spec.target:
#             self.set_brightness(spec.target)
#         if spec.clear_when_done and spec.target == 0:
#             self._safe_clear()
#
#     @staticmethod
#     def _levels(spec: _FadeSpec):
#         # Yield clamped levels using easing over normalized time k/steps
#         delta = spec.target - spec.start
#         total = spec.total_steps
#         for k in range(1, total + 1):
#             progress = spec.easing(k / total)
#             level = spec.start + int(round(progress * delta))
#             yield max(0, min(100, level))
#
#     # ---------- Utilities ----------
#
#     @staticmethod
#     def _linear(t: float) -> float:
#         return t
#
#     @staticmethod
#     def _safe_call(fn) -> None:
#         if callable(fn):
#             try:
#                 fn()
#             except Exception:
#                 pass
#
#     @staticmethod
#     def _safe_setattr(obj, name: str, value) -> None:
#         try:
#             setattr(obj, name, value)
#         except Exception:
#             pass
#
#     @staticmethod
#     def _safe_join(thread, *, timeout: float) -> None:
#         try:
#             if thread.is_alive():
#                 thread.join(timeout=timeout)
#         except Exception:
#             pass
#
#     def _safe_clear(self) -> None:
#         if hasattr(self, 'clear'):
#             try:
#                 self.clear()
#             except Exception:
#                 pass
#
#     @staticmethod
#     def _norm_pct(val: Union[int, float, str]) -> int:
#         if isinstance(val, str):
#             val = float(val.strip('%'))
#         pct = int(round(float(val)))
#         if not (0 <= pct <= 100):
#             raise ValueError('Percentage must be between 0 and 100')
#         return pct
