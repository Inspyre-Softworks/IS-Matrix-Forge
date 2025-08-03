import contextlib
import threading
import types
import sys
import importlib.util
from pathlib import Path

# Provide a minimal is_matrix_forge.log_engine so the helper module can import it
log_engine = types.ModuleType("is_matrix_forge.log_engine")
class DummyLogger:
    def get_child(self, name):
        return self
    def warning(self, *a, **kw):
        pass
ROOT_LOGGER = DummyLogger()
log_engine.ROOT_LOGGER = ROOT_LOGGER
pkg = types.ModuleType("is_matrix_forge")
pkg.log_engine = log_engine
sys.modules["is_matrix_forge"] = pkg
sys.modules["is_matrix_forge.log_engine"] = log_engine

# Load the threading helper module directly from its path
spec = importlib.util.spec_from_file_location(
    "threading_helpers",
    Path(__file__).resolve().parents[1] / "is_matrix_forge/led_matrix/controller/helpers/threading.py",
)
threading_helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(threading_helpers)

synchronized = threading_helpers.synchronized


class DummyBreather:
    def __init__(self):
        self.pause_count = 0

    @property
    def paused(self):
        @contextlib.contextmanager
        def _ctx():
            self.pause_count += 1
            try:
                yield
            finally:
                self.pause_count -= 1
        return _ctx


class DummyController:
    def __init__(self):
        self.breather = DummyBreather()
        self._cmd_lock = threading.RLock()
        self._thread_safe = True
        self._warn_on_thread_misuse = False
        self._owner_thread_id = threading.get_ident()

    @synchronized
    def check_pause(self):
        return self.breather.pause_count


def test_synchronized_pauses_breather():
    ctrl = DummyController()
    assert ctrl.breather.pause_count == 0
    inside_count = ctrl.check_pause()
    assert inside_count == 1
    assert ctrl.breather.pause_count == 0
