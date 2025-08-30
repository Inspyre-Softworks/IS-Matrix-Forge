from __future__ import annotations
from typing import Callable, Iterator
from .fade_spec import FadeSpec

class Levels:
    @staticmethod
    def iter(spec: FadeSpec, *, easing: Callable[[float], float]) -> Iterator[int]:
        delta = spec.target - spec.start
        total = spec.total_steps
        for k in range(total + 1):
            progress = easing(k / total) if total else 1.0
            level = spec.start + int(round(progress * delta))
            yield max(0, min(100, level))
