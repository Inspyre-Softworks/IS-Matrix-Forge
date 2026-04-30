from __future__ import annotations


class Percent:
    """
    Author: Inspyre Softworks
    File: percent.py

    Description:
        A robust percentage utility class that normalizes and resolves
        absolute or relative percentage values with optional fractional
        precision.

        The class can interpret strings such as '+5%', '-10', or '85.5%'
        and compute ratios of two numbers (current vs. maximum) safely,
        with optional clamping and rounding.

    Methods:
        norm(val: int | float | str, *, precision: int = 0) -> float:
            Normalize a numeric or string representation of a percentage
            to a bounded float or integer (0–100).

        resolve(target: int | float | str, *, current: float, precision: int = 0) -> float:
            Resolve a target percentage relative to a current value, optionally
            allowing fractional precision. Supports relative expressions such
            as '+5%', '-2.5', etc.

        from_ratio(current: float, maximum: float, *, precision: int = 0) -> float:
            Convert a ratio of `current / maximum` into a percentage value,
            handling division by zero and clamping the result to [0, 100].

    Raises:
        ValueError:
            Raised when normalization or ratio inputs are invalid.

    Example Usage:
        >>> Percent.from_ratio(25, 50)
        50
        >>> Percent.from_ratio(3.5, 7.0, precision=1)
        50.0
        >>> Percent.from_ratio(110, 100)
        100
    """

    @staticmethod
    def norm(val: int | float | str, *, precision: int = 0) -> float:
        if isinstance(val, str):
            val = float(val.strip('%'))
        pct = round(float(val), precision)
        if not (0 <= pct <= 100):
            raise ValueError('Percentage must be between 0 and 100')
        return pct

    @staticmethod
    def resolve(target: int | float | str, *, current: float, precision: int = 0) -> float:
        if not isinstance(target, str):
            return Percent.norm(target, precision=precision)

        s = target.strip()
        if s.startswith(('+', '-')):
            sign = 1 if s[0] == '+' else -1
            num = s[1:].strip()
            if num.endswith('%'):
                num = num[:-1].strip()
            delta = float(num)
            new_val = current + sign * delta
            return max(0, min(100, round(new_val, precision)))

        return Percent.norm(s, precision=precision)

    @staticmethod
    def from_ratio(current: float, maximum: float, *, precision: int = 0) -> float:
        """
        Compute a percentage from a current and maximum value.

        Parameters:
            current (float):
                The current or partial value.
            maximum (float):
                The maximum or total value. Must be > 0.
            precision (int):
                Number of decimal places to retain. Defaults to 0 (integer).

        Returns:
            float:
                The computed percentage value, clamped to [0, 100].

        Raises:
            ValueError:
                If `maximum` is zero or negative.

        Example Usage:
            >>> Percent.from_ratio(25, 50)
            50
            >>> Percent.from_ratio(3.5, 7.0, precision=1)
            50.0
            >>> Percent.from_ratio(150, 100)
            100
        """
        if maximum <= 0:
            raise ValueError('Maximum must be greater than zero.')

        pct = (current / maximum) * 100
        return max(0, min(100, round(pct, precision)))
