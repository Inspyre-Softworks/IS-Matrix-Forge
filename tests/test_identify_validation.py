import pytest


def test_identify_rejects_non_positive_params(monkeypatch):
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController
    from is_matrix_forge.led_matrix.controller.components import identify as identify_mod

    # Patch raw show to avoid touching hardware
    monkeypatch.setattr(identify_mod, "_show_string_raw", lambda dev, msg: None)

    class Dev:
        name = 'TestDev'
        location = None
        serial_number = 'SN123'

    ctrl = LEDMatrixController(
        Dev(),
        skip_all_init_animations=True,
        skip_init_brightness_set=True,
    )

    with pytest.raises(ValueError, match='duration must be a positive number'):
        ctrl.identify(skip_clear=True, duration=0, cycles=1)

    with pytest.raises(ValueError, match='cycles must be a positive integer'):
        ctrl.identify(skip_clear=True, duration=1.0, cycles=0)

