import functools
import threading

from is_matrix_forge.log_engine import ROOT_LOGGER as PARENT_LOGGER


def synchronized(method=None, *, pause_breather=True):
    """
    Decorator that serializes command execution and integrates with breather pause.

    Behavior:
    - If ``thread_safe=True``, uses ``self._cmd_lock`` (an ``RLock``) to ensure
      in-object mutual exclusion for device operations.
    - Logs a warning if invoked from a non-owner thread while ``thread_safe`` is
      False (misuse detection) provided ``_warn_on_thread_misuse`` is True.
    - When ``pause_breather=True``, it tries to pause any active breathing effect
      around the wrapped call. Resolution order:
        1. ``self.breather.paused`` (preferred)
        2. ``self.breather_paused`` (compatibility helper)

    Usage:
        @synchronized
        def foo(...): ...

        @synchronized(pause_breather=True)
        def draw_grid(...): ...
    """
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            cur_thread_id = threading.get_ident()

            # ⚠️ misuse detection: warn if another thread calls while thread_safe is False
            if (
                not getattr(self, "_thread_safe", False)
                and getattr(self, "_warn_on_thread_misuse", True)
                and cur_thread_id != getattr(self, "_owner_thread_id", None)
            ):
                PARENT_LOGGER.warning(
                    "%r called from thread %r but thread_safe=False",
                    self,
                    threading.current_thread().name
                )

            ctx = None
            if pause_breather:
                # Try to get the Breather context manager in a robust way
                breather = getattr(self, "breather", None)
                if breather is not None and hasattr(breather, "paused"):
                    ctx = breather.paused
                else:
                    # fallback to legacy or alternate pause context
                    ctx = getattr(self, "breather_paused", None)
                if ctx is None:
                    raise RuntimeError(
                        "Could not find a valid breather pause context. "
                        "Neither 'breather.paused' nor 'breather_paused' are present on this object."
                    )

            if ctx is not None:
                with ctx():
                    return _run_locked(self, method, *args, **kwargs)
            else:
                return _run_locked(self, method, *args, **kwargs)

        return wrapper

    def _run_locked(self, method, *args, **kwargs):
        # 🔐 actual lock if thread_safe=True
        if getattr(self, "_thread_safe", False) and getattr(self, "_cmd_lock", None):
            with self._cmd_lock:
                return method(self, *args, **kwargs)
        # fallback: call method directly
        return method(self, *args, **kwargs)

    return decorator if method is None else decorator(method)
