import types

import pytest


def test_controller_init_order(monkeypatch):
    """
    Verify that LEDMatrixController invokes mixin __init__ in cooperative MRO order.
    Order should be: DeviceBase → DisplayHistoryManager → KeepAliveManager →
    GameManager → AnimationManager → DrawingManager → BrightnessManager → BreatherManager →
    IdentifyManager → Loggable.
    """
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
    from is_matrix_forge.led_matrix.controller.components import keep_alive, animation, drawing, identify, brightness, breather, game
    from is_matrix_forge.led_matrix.controller.components import history as history_mod
    from is_matrix_forge.led_matrix.controller import base as base_mod
    from is_matrix_forge import log_engine

    order = []

    def wrap_init(cls, name):
        orig = cls.__init__

        def wrapped(self, *args, **kwargs):
            # Only track calls on the LEDMatrixController instance itself, not
            # on helper objects (e.g. Breather) that are created during init and
            # happen to inherit from some of the same mixins.
            if isinstance(self, LEDMatrixController):
                order.append(name)
            return orig(self, *args, **kwargs)

        return orig, wrapped

    patches = []
    for mod, cls_name in [
        (base_mod, 'DeviceBase'),
        (history_mod, 'DisplayHistoryManager'),
        (keep_alive, 'KeepAliveManager'),
        (game, 'GameManager'),
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
        location = '1-4.2'
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
        'DisplayHistoryManager',
        'KeepAliveManager',
        'GameManager',
        'AnimationManager',
        'DrawingManager',
        'BrightnessManager',
        'BreatherManager',
        'IdentifyManager',
        'Loggable',
    ]


def test_controller_init_rejects_unknown_device_location():
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
    from is_matrix_forge.led_matrix.helpers.location import UnknownDeviceLocationError

    class Dev:
        name = 'TestDev'
        location = '9-9.9'
        serial_number = 'SN123'

    with pytest.raises(UnknownDeviceLocationError, match='Unknown controller location'):
        LEDMatrixController(
            Dev(),
            thread_safe=False,
            skip_all_init_animations=True,
            skip_init_brightness_set=True,
        )


def test_controller_init_normalizes_windows_style_device_location():
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController

    class Dev:
        name = 'TestDev'
        location = '1-3.3:x.4'
        serial_number = 'SN123'

    ctrl = LEDMatrixController(
        Dev(),
        thread_safe=False,
        skip_all_init_animations=True,
        skip_init_brightness_set=True,
    )

    assert ctrl.location['abbrev'] == 'R2'
    assert ctrl.side_of_keyboard == 'right'
    assert ctrl.slot == 2

