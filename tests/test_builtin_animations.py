from __future__ import annotations

import pytest

from is_matrix_forge.led_matrix.controller.components.animation import AnimationManager
from is_matrix_forge.led_matrix.display import animations


def test_available_animation_names_are_stable_and_sorted() -> None:
    assert animations.available_animations() == (
        'checkerboard_cycle',
        'flash',
        'goodbye',
    )
    assert AnimationManager.available_animations() == animations.available_animations()


def test_builtin_animation_names_accept_hyphens() -> None:
    assert animations.get_builtin_animation('checkerboard-cycle') is animations.checkerboard_cycle


def test_unknown_builtin_animation_lists_valid_choices() -> None:
    with pytest.raises(ValueError, match='Available: checkerboard_cycle, flash, goodbye'):
        animations.get_builtin_animation('missing')


def test_controller_can_run_a_builtin_animation_by_name(monkeypatch) -> None:
    calls = []
    manager = object.__new__(AnimationManager)
    manager._thread_safe = False
    manager._warn_on_thread_misuse = False
    monkeypatch.setattr(
        animations,
        'run_builtin_animation',
        lambda controller, name, **options: calls.append((controller, name, options)),
    )

    manager.play_builtin_animation('flash', num_flashes=2, interval=0)

    assert calls == [(manager, 'flash', {'num_flashes': 2, 'interval': 0})]
