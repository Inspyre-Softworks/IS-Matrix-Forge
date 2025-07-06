import functools
import threading

from is_matrix_forge.log_engine import ROOT_LOGGER as PARENT_LOGGER


def synchronized(method):
    """
    Lock & warn if you’re calling off-thread with thread_safe=False.

    Parameters:
        method (callable): The method to wrap.

    Returns:
        Callable: The wrapped method that will log/lock appropriately.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        cur_thread_id = threading.get_ident()

        # ⚠️ misuse detection: warn if another thread calls while thread_safe is False
        if (
            not getattr(self, "_thread_safe", False)
            and getattr(self, "_warn_on_thread_misuse", True)
            and cur_thread_id != getattr(self, "_owner_thread_id", None)
        ):
            PARENT_LOGGER.warn_once(f"{self} called from thread {threading.current_thread()} but thread_safe=False")

        # 🔐 actual lock if thread_safe=True
        if getattr(self, "_thread_safe", False) and getattr(self, "_cmd_lock", None):
            with self._cmd_lock:
                return method(self, *args, **kwargs)

        # fallback: call method directly
        return method(self, *args, **kwargs)

    return wrapper
