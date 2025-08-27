import types

import pytest


def test_controller_init_order(monkeypatch):
    """
    Verify that LEDMatrixController invokes mixin __init__ in cooperative MRO order.
    Order should be: DeviceBase → KeepAliveManager → AnimationManager →
    DrawingManager → BrightnessManager → BreatherManager → IdentifyManager → Loggable.
    """
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
    from is_matrix_forge.led_matrix.controller.components import keep_alive, animation, drawing, identify, brightness, breather
    from is_matrix_forge.led_matrix.controller import base as base_mod
    from is_matrix_forge import log_engine

    order = []

    def wrap_init(cls, name):
        orig = cls.__init__

        def wrapped(self, *args, **kwargs):
            order.append(name)
            return orig(self, *args, **kwargs)

        return orig, wrapped

    patches = []
    for mod, cls_name in [
        (base_mod, 'DeviceBase'),
        (keep_alive, 'KeepAliveManager'),
        (animation, 'AnimationManager'),
        (drawing, 'DrawingManager'),
        (brightness, 'BrightnessManager'),
        (breather, 'BreatherManager'),
        (identify, 'IdentifyManager'),
    ]:
        cls = getattr(mod, cls_name)
        orig, wrapped = wrap_init(cls, cls_name)
        patches.append((cls, orig))
        monkeypatch.setattr(cls, '__init__', wrapped)

    # Loggable (stub) lives in log_engine
    Loggable = log_engine.Loggable
    orig_loggable, wrapped_loggable = wrap_init(Loggable, 'Loggable')
    patches.append((Loggable, orig_loggable))
    monkeypatch.setattr(Loggable, '__init__', wrapped_loggable)

    class Dev:
        name = 'TestDev'
        location = None
        serial_number = 'SN123'

    # Avoid hardware side-effects during init
    ctrl = LEDMatrixController(
        Dev(),
        thread_safe=False,
        skip_all_init_animations=True,
        skip_init_brightness_set=True,
    )

    assert order == [
        'DeviceBase',
        'KeepAliveManager',
        'AnimationManager',
        'DrawingManager',
        'BrightnessManager',
        'BreatherManager',
        'IdentifyManager',
        'Loggable',
    ]

