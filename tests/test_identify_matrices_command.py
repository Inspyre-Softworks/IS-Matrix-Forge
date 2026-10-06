"""Tests for concurrent matrix identification from the CLI."""

from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import patch


class _Controller:
    def __init__(self, barrier: threading.Barrier) -> None:
        self.barrier = barrier
        self.calls = []
        self.thread_id = None

    def identify(self, **kwargs) -> None:
        self.thread_id = threading.get_ident()
        self.calls.append(kwargs)
        self.barrier.wait(timeout=2)


def test_identify_matrices_runs_controllers_concurrently() -> None:
    """Each selected matrix should run its blocking identify routine in parallel."""
    from is_matrix_forge.led_matrix.Scripts.led_matrix import identify_matrices_command

    barrier = threading.Barrier(2)
    controllers = [_Controller(barrier), _Controller(barrier)]
    cli_args = SimpleNamespace(skip_clear=True, runtime="4.5", cycle_count="3")

    with patch(
        "is_matrix_forge.led_matrix.Scripts.led_matrix.execute_get_controllers",
        return_value=controllers,
    ):
        identify_matrices_command(cli_args)

    expected = {"skip_clear": True, "duration": 4.5, "cycles": 3}
    assert [controller.calls for controller in controllers] == [[expected], [expected]]
    worker_thread_ids = {controller.thread_id for controller in controllers}
    assert len(worker_thread_ids) == 2
    assert threading.get_ident() not in worker_thread_ids
