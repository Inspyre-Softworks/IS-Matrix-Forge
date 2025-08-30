from __future__ import annotations

class Percent:
    @staticmethod
    def norm(val: int | float | str) -> int:
        if isinstance(val, str):
            s = val.strip()
            if s.endswith('%'):
                s = s[:-1].strip()
            val = float(s)
        pct = int(round(float(val)))
        if not (0 <= pct <= 100):
            raise ValueError('Percentage must be between 0 and 100')
        return pct

    @staticmethod
    def resolve(target: int | float | str, *, current: int) -> int:
        if not isinstance(target, str):
            return Percent.norm(target)
        s = target.strip()
        if s.startswith(('+', '-')):
            sign = 1 if s[0] == '+' else -1
            num = s[1:].strip()
            if num.endswith('%'):
                num = num[:-1].strip()
            delta = float(num)
            return max(0, min(100, int(round(current + sign * delta))))
        return Percent.norm(s)
