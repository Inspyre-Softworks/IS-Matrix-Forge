import functools
import threading

from is_matrix_forge.log_engine import ROOT_LOGGER as PARENT_LOGGER


def synchronized(method=None, *, pause_breather=True):
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            cur_thread_id = threading.get_ident()

            if (
                not getattr(self, '_thread_safe', False)
                and getattr(self, '_warn_on_thread_misuse', True)
                and cur_thread_id != getattr(self, '_owner_thread_id', None)
            ):
                PARENT_LOGGER.warning(
                    '%r called from thread %r but thread_safe=False',
                    self, threading.current_thread().name
                )

            ctx_factory = None
            if pause_breather:
                breather = getattr(self, 'breather', None)
                if breather is not None and hasattr(breather, 'paused'):
                    ctx_factory = breather.paused
                else:
                    ctx_factory = getattr(self, 'breather_paused', None)

            # Soft-fallback: if no context is available, just proceed (don’t raise)
            if ctx_factory is not None:
                with ctx_factory():
                    return _run_locked(self, method, *args, **kwargs)
            return _run_locked(self, method, *args, **kwargs)
        return wrapper

    def _run_locked(self, method, *args, **kwargs):
        lock = getattr(self, '_cmd_lock', None)
        if getattr(self, '_thread_safe', False) and lock is not None:
            with lock:  # expected to be an RLock
                return method(self, *args, **kwargs)
        return method(self, *args, **kwargs)

    return decorator if method is None else decorator(method)
