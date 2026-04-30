"""Tests for the scroll_text_command --sequential and --span-matrices logic.

These tests verify that:
* ``--sequential`` with horizontal direction builds spanning animations (single screen).
* ``--sequential`` with vertical directions plays all controllers concurrently.
* Combining ``--sequential`` and ``--span-matrices`` raises an error.
* ``--span-matrices`` with a non-horizontal direction raises an error.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stubs for optional runtime dependencies
# ---------------------------------------------------------------------------

def _install_test_stubs() -> None:
    """Provide lightweight stand-ins for optional runtime dependencies."""

    if "is_matrix_forge.common.dirs" not in sys.modules:
        m = ModuleType("is_matrix_forge.common.dirs")
        m.APP_DIRS = type("_D", (), {"user_data_path": Path("/tmp/led-matrix")})()
        m.APP_DIR = Path("/tmp/led-matrix")
        m.PRESETS_DIR = Path("/tmp/led-matrix/presets")
        sys.modules["is_matrix_forge.common.dirs"] = m

    if "is_matrix_forge.led_matrix.helpers.device" not in sys.modules:
        m = ModuleType("is_matrix_forge.led_matrix.helpers.device")
        m.DEVICES = []
        m.get_devices = lambda *a, **kw: []
        sys.modules["is_matrix_forge.led_matrix.helpers.device"] = m

    if "is_matrix_forge.led_matrix.controller.controller" not in sys.modules:
        m = ModuleType("is_matrix_forge.led_matrix.controller.controller")

        class LEDMatrixController:  # pragma: no cover
            pass

        m.LEDMatrixController = LEDMatrixController
        sys.modules["is_matrix_forge.led_matrix.controller.controller"] = m


_install_test_stubs()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cli_args(
    direction: str = "h",
    sequential: bool = False,
    span_matrices: bool = False,
    only_left: bool = False,
    only_right: bool = False,
    input_text: str = "hello",
    frame_duration: float = 0.33,
) -> MagicMock:
    """Return a minimal argparse-namespace stand-in for scroll_text_command."""
    ns = MagicMock()
    ns.direction = direction
    ns.sequential = sequential
    ns.span_matrices = span_matrices
    ns.only_left = only_left
    ns.only_right = only_right
    ns.input = input_text
    ns.frame_duration = frame_duration
    return ns


def _make_controller(name: str = "ctrl") -> MagicMock:
    ctrl = MagicMock()
    ctrl.name = name
    return ctrl


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSequentialSingleScreen:
    """--sequential must treat all matrices as a unified screen."""

    def _run_command(self, cli_args, controllers):
        """Invoke scroll_text_command with the given controllers, fully mocked."""
        from is_matrix_forge.led_matrix.Scripts.led_matrix import scroll_text_command

        sentinel_animation = object()

        with (
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix.execute_get_controllers",
                return_value=controllers,
            ),
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix._build_horizontal_span_animations",
                return_value={c: sentinel_animation for c in controllers},
            ) as mock_build_span,
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix.run_with_guard",
            ) as mock_run,
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix._order_controllers_for_span",
                side_effect=lambda c: list(c),
            ) as mock_order,
        ):
            try:
                scroll_text_command(cli_args)
            except SystemExit:
                raise

            return mock_build_span, mock_run, mock_order

    def test_sequential_horizontal_builds_span_animations(self) -> None:
        """``--sequential`` with ``-d h`` must build horizontal span animations."""
        controllers = [_make_controller("L1"), _make_controller("R1")]
        cli_args = _make_cli_args(direction="h", sequential=True)

        mock_build_span, mock_run, mock_order = self._run_command(cli_args, controllers)

        mock_build_span.assert_called_once()
        mock_order.assert_called_once()

    def test_sequential_horizontal_runs_all_controllers_in_single_invoke(self) -> None:
        """``--sequential`` must NOT loop over controllers one at a time.

        The activator must be invoked exactly ONCE with all controllers together,
        not once per controller.
        """
        controllers = [_make_controller("L1"), _make_controller("R1")]
        cli_args = _make_cli_args(direction="h", sequential=True)

        _, mock_run, _ = self._run_command(cli_args, controllers)

        # run_with_guard (which backs invoke) must be called exactly once
        assert mock_run.call_count == 1

    def test_sequential_vertical_does_not_build_span_animations(self) -> None:
        """``--sequential`` with vertical direction must NOT build horizontal span animations.

        For vertical, all matrices play the same animation concurrently — no
        horizontal spanning is needed.
        """
        controllers = [_make_controller("L1"), _make_controller("R1")]
        cli_args = _make_cli_args(direction="up", sequential=True)

        mock_build_span, mock_run, _ = self._run_command(cli_args, controllers)

        mock_build_span.assert_not_called()

    def test_sequential_vertical_runs_all_controllers_in_single_invoke(self) -> None:
        """Vertical ``--sequential`` must invoke the activator once (not per-controller)."""
        controllers = [_make_controller("L1"), _make_controller("R1")]
        cli_args = _make_cli_args(direction="up", sequential=True)

        _, mock_run, _ = self._run_command(cli_args, controllers)

        assert mock_run.call_count == 1


class TestSequentialSpanMutualExclusion:
    """--sequential and --span-matrices cannot be combined."""

    def test_sequential_and_span_raises_system_exit(self) -> None:
        """Combining --sequential and --span-matrices must exit with an error."""
        controllers = [_make_controller("L1"), _make_controller("R1")]
        cli_args = _make_cli_args(direction="h", sequential=True, span_matrices=True)

        from is_matrix_forge.led_matrix.Scripts.led_matrix import scroll_text_command

        with (
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix.execute_get_controllers",
                return_value=controllers,
            ),
            pytest.raises(SystemExit),
        ):
            scroll_text_command(cli_args)


class TestSpanMatricesDirectionRestriction:
    """--span-matrices requires --direction h."""

    def test_span_matrices_with_vertical_raises_system_exit(self) -> None:
        """``--span-matrices`` with a vertical direction must exit with an error."""
        controllers = [_make_controller("L1"), _make_controller("R1")]
        cli_args = _make_cli_args(direction="up", sequential=False, span_matrices=True)

        from is_matrix_forge.led_matrix.Scripts.led_matrix import scroll_text_command

        with (
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix.execute_get_controllers",
                return_value=controllers,
            ),
            pytest.raises(SystemExit),
        ):
            scroll_text_command(cli_args)


class TestFrameDurationForwarding:
    """frame_duration must be forwarded to scroll_text in the non-span path."""

    def _run_and_capture_scroll_text_calls(self, cli_args, controllers):
        """Run scroll_text_command and return the calls made to controller.scroll_text."""
        from is_matrix_forge.led_matrix.Scripts.led_matrix import scroll_text_command

        ctrl = controllers[0]
        captured_kwargs = []

        def fake_scroll_text(text, **kwargs):
            captured_kwargs.append(kwargs)

        ctrl.scroll_text.side_effect = fake_scroll_text
        ctrl.keep_alive = False

        with (
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix.execute_get_controllers",
                return_value=controllers,
            ),
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix.run_with_guard",
                side_effect=lambda targets, **kwargs: kwargs["activator"](targets, None),
            ),
            patch(
                "is_matrix_forge.led_matrix.Scripts.led_matrix._run_operation",
                side_effect=lambda devices, operation, **kwargs: [operation(c) for c in devices],
            ),
        ):
            scroll_text_command(cli_args)

        return captured_kwargs

    def test_default_frame_duration_forwarded(self) -> None:
        """Default frame_duration (0.33) must be passed to scroll_text."""
        controllers = [_make_controller("C1")]
        cli_args = _make_cli_args(direction="up", frame_duration=0.33)

        calls = self._run_and_capture_scroll_text_calls(cli_args, controllers)

        assert len(calls) == 1
        assert calls[0]["frame_duration"] == pytest.approx(0.33)

    def test_custom_frame_duration_forwarded(self) -> None:
        """Explicit frame_duration must be forwarded to scroll_text."""
        controllers = [_make_controller("C1")]
        cli_args = _make_cli_args(direction="up", frame_duration=0.1)

        calls = self._run_and_capture_scroll_text_calls(cli_args, controllers)

        assert len(calls) == 1
        assert calls[0]["frame_duration"] == pytest.approx(0.1)
