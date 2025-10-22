from __future__ import annotations


class Easing:
    @staticmethod
    def linear(t: float) -> float:
        return t

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2

    @staticmethod
    def ease_out_quint(t: float) -> float:
        return 1 - (1 - t) ** 5
