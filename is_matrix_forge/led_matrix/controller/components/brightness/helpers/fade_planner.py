from __future__ import annotations
from typing import Optional
from .fade_spec import FadeSpec

class FadePlanner:
    @staticmethod
    def calc_steps(start: int, target: int, steps: Optional[int], duration: float, fps: int) -> int:
        if steps and steps > 0:
            return steps
        delta = abs(target - start)
        perceptual = max(1, int(round(duration * fps)))
        return max(1, min(delta, perceptual))

    @staticmethod
    def make_spec(*, start: int, target: int, duration: float, fps: int,
                  steps: Optional[int] = None, max_steps: Optional[int] = None,
                  min_step_delay: Optional[float] = None, clear_when_done: bool = False) -> FadeSpec:
        total = FadePlanner.calc_steps(start, target, steps, duration, fps)
        if max_steps:
            total = min(total, max_steps)
        delay = (duration / total) if duration > 0 else 0.0
        if min_step_delay:
            delay = max(delay, min_step_delay)
        return FadeSpec(start=max(0, min(100, start)), target=max(0, min(100, target)),
                        total_steps=total, step_delay=delay, clear_when_done=clear_when_done)
