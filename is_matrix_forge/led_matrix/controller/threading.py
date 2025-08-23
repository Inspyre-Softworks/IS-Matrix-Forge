"""Thread safety utilities for the controller façade."""

from __future__ import annotations

import functools
import threading
from typing import Callable


def synchronized(method: Callable | None = None):
    """Decorator that acquires the controller's command lock if available."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, '_cmd_lock', None)
            if lock is not None:
                with lock:
                    return func(self, *args, **kwargs)
            return func(self, *args, **kwargs)

        return wrapper

    return decorator if method is None else decorator(method)


class ThreadSafetyMixin:
    """Provide basic thread-safety primitives."""

    def _thread_safe_setup(self, thread_safe: bool = False, warn_on_thread_misuse: bool = True) -> None:
        self._thread_safe = bool(thread_safe)
        self._warn_on_thread_misuse = bool(warn_on_thread_misuse)
        self._owner_thread_id = threading.get_ident()
        self._cmd_lock = threading.RLock() if self._thread_safe else None

