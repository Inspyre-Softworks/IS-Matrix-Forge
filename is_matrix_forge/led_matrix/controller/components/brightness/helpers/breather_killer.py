from __future__ import annotations
from typing import Tuple
from .safe_ops import SafeOps

class BreatherKiller:
    def __init__(self, *, stop_verbs: Tuple[str, ...] = ('stop', 'shutdown', 'disable', 'kill', 'cancel'),
                 flags_off: Tuple[str, ...] = ('enabled', 'running', 'active'),
                 worker_attrs: Tuple[str, ...] = ('thread', 'worker', '_thread', '_worker')):
        self._stop_verbs = stop_verbs
        self._flags_off = flags_off
        self._worker_attrs = worker_attrs

    def kill(self, owner) -> None:
        b = getattr(owner, 'breather', None)
        if not b:
            return
        for name in self._stop_verbs:
            SafeOps.call(getattr(b, name, None))
        for flag in self._flags_off:
            if hasattr(b, flag):
                SafeOps.setattr(b, flag, False)
        for attr in self._worker_attrs:
            t = getattr(b, attr, None)
            if t is not None and getattr(t, 'is_alive', None):
                SafeOps.join(t, timeout=0.1)
