from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class FadeSpec:
    start: int
    target: int
    total_steps: int
    step_delay: float
    clear_when_done: bool
