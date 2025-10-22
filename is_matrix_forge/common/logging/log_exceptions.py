from __future__ import annotations

import logging
from functools import wraps
from threading import Thread
from typing import Any, Callable, Optional

from is_matrix_forge.log_engine import ROOT_LOGGER

MOD_LOGGER = ROOT_LOGGER.get_child('controller.helpers.silent_ops')


def _norm_level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.DEBUG)
    return logging.DEBUG


def log_on_exception(
    *,
    level: int | str = 'debug',
    reraise: bool = False,
    logger_attr: str = 'LOGGER',
    fallback_logger: logging.Logger = MOD_LOGGER,
    msg: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator: log exceptions at `level` with exc_info=True, optionally re-raise.

    - If bound method, uses `self.LOGGER` or `cls.LOGGER` (name configurable via `logger_attr`).
    - Otherwise uses `fallback_logger`.
    """
    lvl = _norm_level(level)

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as e:  # intentionally broad: we're *logging* and (optionally) swallowing
                # find a logger on self/cls if present
                bound_logger = fallback_logger
                if args:
                    candidate = getattr(args[0], logger_attr, None)
                    if isinstance(candidate, logging.Logger):
                        bound_logger = candidate

                text = msg or f'Exception in {fn.__qualname__}: {e!r}'
                bound_logger.log(lvl, text, exc_info=True)
                if reraise:
                    raise
                # swallow: return None
        return wrapper
    return deco


class SilentOps:
    """Tiny utility surface that does things quietly but logs failures at DEBUG."""

    LOGGER = ROOT_LOGGER.get_child('controller.helpers.silent_ops')

    @classmethod
    @log_on_exception(level='debug', reraise=False)  # no repeats; logger inferred from cls.LOGGER
    def join(cls, thread: Thread, *, timeout: Optional[float] = None) -> None:
        if thread and thread.is_alive():
            thread.join(timeout=timeout)

    @classmethod
    @log_on_exception(level='debug', reraise=False)
    def setattr(cls, obj: Any, name: str, value: Any) -> None:
        setattr(obj, name, value)

    @classmethod
    @log_on_exception(level='debug', reraise=False)
    def clear(cls, device_obj: Any) -> None:
        if hasattr(device_obj, 'clear'):
            device_obj.clear()
