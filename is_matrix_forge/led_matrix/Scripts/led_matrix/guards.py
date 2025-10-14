"""Utilities that manage controller lifecycle threads for CLI commands."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable


LOGGER = logging.getLogger(__name__)


def _ensure_positive_duration(value):
    if value is None:
        return None

    if value <= 0:
        raise SystemExit('--run-for duration must be greater than zero seconds when provided.')

    return value


def _cleanup_controllers(controllers: Iterable, *, clear_after: bool) -> None:
    cleanup_errors: list[Exception] = []

    for controller in controllers:
        try:
            controller.keep_alive = False
        except Exception as exc:  # noqa: BLE001 - best-effort cleanup
            LOGGER.exception('Exception while disabling keep_alive for %r', controller)
            cleanup_errors.append(exc)

        if not clear_after:
            continue

        try:
            controller.clear()
        except AttributeError:
            try:
                controller.clear_grid()
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                LOGGER.exception('Exception while clearing grid for %r', controller)
                cleanup_errors.append(exc)
        except Exception as exc:  # noqa: BLE001 - best-effort cleanup
            LOGGER.exception('Exception while clearing display for %r', controller)
            cleanup_errors.append(exc)

    if cleanup_errors:
        messages = '\n'.join(str(err) for err in cleanup_errors)
        raise SystemExit(f'Cleanup encountered issues:\n{messages}')


def run_with_guard(
    controllers: Iterable,
    *,
    run_for,
    clear_after: bool,
    activator: Callable[[Iterable, threading.Event], None],
    thread_name: str,
    wait_for_interrupt: bool = False,
) -> None:
    """Execute an action while keeping controllers alive until timeout or interruption.

    Parameters:
        controllers:
            The controller collection to operate on.
        run_for:
            Optional duration in seconds before the guard triggers cleanup.
        clear_after:
            Whether to clear each controller once the guard finishes.
        activator:
            Callable that performs the desired work while the guard thread runs.
        thread_name:
            Name assigned to the guard thread for easier debugging.
        wait_for_interrupt:
            When ``True`` and no duration is provided, the guard waits for an
            external interrupt (such as Ctrl+C) instead of stopping once the
            activator completes.
    """

    duration = _ensure_positive_duration(run_for)
    stop_event = threading.Event()

    def guard() -> None:
        try:
            if duration is None:
                stop_event.wait()
            else:
                stop_event.wait(timeout=duration)
        finally:
            try:
                _cleanup_controllers(controllers, clear_after=clear_after)
            finally:
                stop_event.set()

    sentinel = threading.Thread(name=thread_name, target=guard, daemon=True)
    sentinel.start()

    try:
        activator(controllers, stop_event)
    except Exception:
        stop_event.set()
        sentinel.join()
        raise
    else:
        if duration is None and not wait_for_interrupt:
            stop_event.set()

    try:
        while sentinel.is_alive():
            sentinel.join(timeout=0.2)
    except KeyboardInterrupt:
        stop_event.set()
        sentinel.join()

