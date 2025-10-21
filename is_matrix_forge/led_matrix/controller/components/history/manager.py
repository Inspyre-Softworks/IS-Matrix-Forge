from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from time import time
from typing import Any, Deque, Literal, Optional

from .event import DisplayEvent


class DisplayHistoryManager:
    """
    Mixin that records a rolling history of what's been shown, exposes the
    current display, supports go_back(n), and can restore the last brightness.
    """

    def __init__(self, *, history_maxlen: int = 256, **kwargs):
        # History fields must exist before any parent init triggers draws.
        self._display_history: Deque[DisplayEvent] = deque(maxlen=history_maxlen)
        self._current_event: Optional[DisplayEvent] = None

        # Brightness tracking
        self._current_brightness: Optional[int] = self._get_brightness()
        self._last_brightness: Optional[int] = None

        super().__init__(**kwargs)

    # --- Public API ---------------------------------------------------------------

    @property
    def current_display(self) -> Optional[DisplayEvent]:
        return self._current_event

    @property
    def current_grid(self) -> Optional[list[list[int]]]:
        return self._current_event.grid if self._current_event else None

    @property
    def display_history(self) -> tuple[DisplayEvent, ...]:
        return tuple(self._display_history)

    def restore_last_brightness(self) -> Optional[int]:
        """
        Revert brightness to the most recent previous value (if known).
        Returns the brightness restored, or None if no prior value.
        """
        if self._last_brightness is None:
            return None
        target = self._last_brightness
        # Using our wrapper ensures we also record the change.
        self.set_brightness(target)
        return target

    # --- Internals ----------------------------------------------------------------

    def _record_event(
        self,
        kind: DisplayEvent.__annotations__['kind'],
        *,
        meta: Optional[dict[str, Any]] = None,
        grid: Optional[list[list[int]]] = None,
    ) -> None:
        if not hasattr(self, '_display_history') or self._display_history is None:
            self._display_history = deque(maxlen=256)

        # Always try to include current brightness in event metadata (if available)
        m = dict(meta or {})
        b = self._get_brightness()
        if b is not None and 'brightness' not in m:
            m['brightness'] = int(b)

        ev = DisplayEvent(ts=time(), kind=kind, meta=m, grid=grid)
        self._current_event = ev
        self._display_history.append(ev)

    def _get_brightness(self) -> Optional[int]:
        """
        Best-effort probe of current brightness across possible controller APIs.
        """
        try:
            if hasattr(self, 'get_brightness') and callable(getattr(self, 'get_brightness')):
                return int(self.get_brightness())  # type: ignore[misc]
        except Exception:
            pass
        for attr in ('brightness', '_brightness', 'default_brightness'):
            try:
                if hasattr(self, attr):
                    val = getattr(self, attr)
                    if val is not None:
                        return int(val)
            except Exception:
                continue
        return None

    # --- History control ----------------------------------------------------------

    def go_back(self, n: int = 1) -> Optional[DisplayEvent]:
        """
        Restore the display from n steps back in history.
        Returns the event restored, or None if invalid / no grid snapshot.
        """
        if not self._display_history:
            return None
        try:
            event = self._display_history[-n] if n > 0 else self._display_history[n]
        except IndexError:
            return None
        if event.grid is None:
            return None
        self.draw_grid(event.grid)
        self._record_event('restore', meta={'source': n}, grid=event.grid)
        return event

    # --- Brightness wrapper -------------------------------------------------------

    def set_brightness(self, value: int, *args, **kwargs):
        """
        Wraps the underlying brightness setter (if any) to track last/current
        brightness and to log a 'brightness' event.
        """
        prev = self._get_brightness()
        # Call downstream implementation if it exists; otherwise try attribute set
        ret = None
        try:
            # If a parent mixin implements set_brightness, this will hit it.
            ret = super().set_brightness(value, *args, **kwargs)  # type: ignore[misc]
        except AttributeError:
            # Fallback: attempt to set a common attribute name
            try:
                setattr(self, 'brightness', int(value))
            except Exception:
                # As a last resort, store locally so restore_last_brightness still works
                self._current_brightness = int(value)

        # Update our trackers
        if prev is not None:
            self._last_brightness = int(prev)
        self._current_brightness = int(value)

        # Record the change
        self._record_event('brightness', meta={'value': int(value), 'prev': prev}, grid=None)
        return ret

    # --- Overridden draw hooks ----------------------------------------------------

    def clear_grid(self, *args, **kwargs):
        ret = super().clear_grid(*args, **kwargs)  # type: ignore[misc]
        grid = None
        try:
            g = getattr(self, '_grid', None)
            grid = [row[:] for row in getattr(g, 'grid', [])] if g is not None else None
        except Exception:
            pass
        self._record_event('clear', meta={}, grid=grid)
        return ret

    def draw_grid(self, grid=None, *args, **kwargs):
        ret = super().draw_grid(grid, *args, **kwargs)  # type: ignore[misc]
        snap = None
        try:
            g = getattr(self, '_grid', None)
            snap = [row[:] for row in getattr(g, 'grid', [])] if g is not None else None
        except Exception:
            pass
        self._record_event('grid', meta={}, grid=snap)
        return ret

    def draw_pattern(self, pattern: str, *args, **kwargs):
        ret = super().draw_pattern(pattern, *args, **kwargs)  # type: ignore[misc]
        self._record_event('pattern', meta={'pattern': str(pattern)}, grid=None)
        return ret

    def draw_percentage(self, n: int, *args, **kwargs):
        ret = super().draw_percentage(n, *args, **kwargs)  # type: ignore[misc]
        self._record_event('percentage', meta={'value': int(n)}, grid=None)
        return ret

    def show_text(self, text: str, *args, **kwargs):
        ret = super().show_text(text, *args, **kwargs)  # type: ignore[misc]
        self._record_event('text', meta={'text': str(text)}, grid=None)
        return ret

    def play_animation(self, animation, *args, **kwargs):
        ret = super().play_animation(animation, *args, **kwargs)  # type: ignore[misc]
        self._record_event('animation', meta={'animation': repr(animation)}, grid=None)
        return ret