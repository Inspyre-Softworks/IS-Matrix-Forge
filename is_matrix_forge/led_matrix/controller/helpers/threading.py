import functools
import threading
from typing import Optional

from is_matrix_forge.log_engine import ROOT_LOGGER as PARENT_LOGGER


def get_breather_context(self, pause_breather):
    """
    Retrieve the breather pause context for the given object.

    This function checks if the breather should be paused and returns the appropriate
    context manager. If `pause_breather` is False, it returns ``None``.  When a
    pause is requested we first look for a dedicated ``breather_paused``
    attribute on the object (some controllers expose a custom context manager
    that fully stops the breathing thread).  If that is not available, we
    fall back to the ``breather.paused`` context provided by the ``Breather``
    helper itself.

    Parameters:
        self:
            The object containing breather attributes.

        pause_breather (bool):
            A flag indicating whether to pause the breather.

    Returns:
        Optional[contextlib.AbstractContextManager]:
            The pause context manager if available, otherwise None.
    """
    if not pause_breather:
        return None

    # Prefer an explicit "breather_paused" context on the object itself.  Some
    # controllers implement a private ``__breather_paused`` method; we attempt
    # to resolve that name‑mangled attribute as well.
    possible_names = (
        "breather_paused",
        "_breather_paused",
        f"_{type(self).__name__}__breather_paused",
    )
    for name in possible_names:
        breather_paused = getattr(self, name, None)
        if breather_paused is not None:
            return breather_paused() if callable(breather_paused) else breather_paused

    # Fall back to the breather's own pause context.
    breather = getattr(self, "breather", None)
    if breather and hasattr(breather, "paused"):
        pause_ctx = breather.paused
        return pause_ctx() if callable(pause_ctx) else pause_ctx

    return None


def should_warn_thread_misuse(self_obj):
    """
    Determine if a warning should be issued for thread misuse.

    This function checks if the current thread is different from the owner thread
    and if the object is not marked as thread-safe. If these conditions are met,
    and warnings for thread misuse are enabled, it returns True.

    Parameters:
        self_obj:
            The object to check for thread safety and misuse warnings.

    Returns:
        bool:
            True if a warning should be issued, False otherwise.
    """
    return (
        not getattr(self_obj, "_thread_safe", False)
        and getattr(self_obj, "_warn_on_thread_misuse", True)
        and threading.get_ident() != getattr(self_obj, "_owner_thread_id", None)
    )

def get_lock(self_obj):

    """
    Get the lock associated with the object.

    Parameters:
        self_obj (object):
            The object to retrieve the lock from.

    Returns:
        threading.Lock or None:
            The lock associated with the object, or None if no lock is defined.
    """
    return getattr(self_obj, "_cmd_lock", None)


def run_with_contexts(ctx, lock, func):

    """
    Run a function with optional context and lock management.

    If a context is provided, it will be entered before calling the given function.
    If a lock is provided, it will be acquired before calling the function and released
    afterwards.

    Parameters:
        ctx (optional):
            A context manager to enter before calling the function.
        lock (optional):
            A lock to acquire before calling the function.
        func (callable):
            The function to call.

    Returns:
        Any:
            The return value of the called function.
    """
    if ctx is not None:
        with ctx:
            if lock:
                with lock:
                    return func()
            return func()
    else:
        if lock:
            with lock:
                return func()
        return func()


# noinspection PyFunctionTooComplex
def synchronized(method=None, *, pause_breather=True):
    """
    Lock & warn if you’re calling off-thread with thread_safe=False.
    Optionally, pause/resume the breather around the method.
    """
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if should_warn_thread_misuse(self):
                PARENT_LOGGER.warning(
                    "%r called from thread %r but thread_safe=False",
                    self,
                    threading.current_thread().name
                )
            ctx = get_breather_context(self, pause_breather)
            if pause_breather and ctx is None:
                raise RuntimeError(
                    "Could not find a valid breather pause context. "
                    "Neither 'breather.paused' nor 'breather_paused' are present on this object."
                )
            lock = get_lock(self)
            return run_with_contexts(ctx, lock, lambda: method(self, *args, **kwargs))
        return wrapper

    return decorator if method is None else decorator(method)
