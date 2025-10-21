import logging
import threading
from typing import Callable, Iterable

from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments import Arguments


LOGGER = logging.getLogger(__name__)

ARGUMENTS = Arguments()


def _filter_controllers_by_side(controllers, cli_args):
    """Return the controllers that match the requested keyboard side."""

    if cli_args is None:
        return controllers

    if getattr(cli_args, 'only_left', False):
        return [
            controller for controller in controllers
            if getattr(controller, 'side_of_keyboard', None) == 'left'
        ]

    if getattr(cli_args, 'only_right', False):
        return [
            controller for controller in controllers
            if getattr(controller, 'side_of_keyboard', None) == 'right'
        ]

    return list(controllers)


def _describe_selection(cli_args):
    if cli_args is None:
        return 'any LED matrix'

    if getattr(cli_args, 'only_left', False):
        return 'the leftmost LED matrix'

    if getattr(cli_args, 'only_right', False):
        return 'the rightmost LED matrix'

    return 'any LED matrix'


def execute_get_controllers(cli_args=None):
    """Return the available controllers honoring any CLI matrix selection.

    Parameters:
        cli_args (Optional[argparse.Namespace]):
            The parsed command-line arguments. When provided, any matrix
            selection flags (``--only-left`` / ``--only-right``) are applied to
            the available controllers.

    Returns:
        List[LEDMatrixController]:
            A list of controller objects, each representing an available LED matrix.
    """
    from is_matrix_forge.led_matrix.controller import get_controllers
    controllers = get_controllers(
        threaded                 = True,
        skip_all_init_animations = True,
        clear_on_init            = True
    )

    if not controllers:
        raise SystemExit('No LED matrices are available.')

    if filtered := _filter_controllers_by_side(controllers, cli_args):
        return filtered

    raise SystemExit(f'No LED matrices matched the requested selection ({_describe_selection(cli_args)}).')


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


def _run_with_guard(
    controllers: Iterable,
    *,
    run_for,
    clear_after: bool,
    activator: Callable[[Iterable, threading.Event], None],
    thread_name: str,
) -> None:
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

    try:
        while sentinel.is_alive():
            sentinel.join(timeout=0.2)
    except KeyboardInterrupt:
        stop_event.set()
        sentinel.join()


def scroll_text_command(cli_args=ARGUMENTS):
    """
    Invokes the command to scroll text on the LED matrix.

    Parameters:
        cli_args (Optional[Arguments]):
            The object that holds the command-line arguments. This is a subclass of `argparse.ArgumentParser`.
            (Defaults to `ARGUMENTS`)

    Returns:
        None
    """
    from .arguments.commands.scroll_text import DIRECTION_MAP
    controllers = execute_get_controllers(cli_args)

    direction = DIRECTION_MAP[cli_args.direction.strip().lower()]
    text = cli_args.input

    def activator(devices, _stop_event):
        for controller in devices:
            controller.keep_alive = True
            controller.scroll_text(text, direction=direction)

    _run_with_guard(
        controllers,
        run_for=None,
        clear_after=False,
        activator=activator,
        thread_name='scroll-text-guard',
    )


def display_text_command(cli_args):
    """Display static text on the selected LED matrices until interrupted."""
    controllers = execute_get_controllers(cli_args)

    clear_after = not cli_args.skip_clear

    def activator(devices, _stop_event):
        for controller in devices:
            controller.keep_alive = True
            controller.show_text(cli_args.text)

    _run_with_guard(
        controllers,
        run_for=cli_args.run_for,
        clear_after=clear_after,
        activator=activator,
        thread_name='display-text-guard',
    )


def identify_matrices_command(cli_args):
    """Run the identification routine on the selected LED matrices.

    Parameters:
        cli_args: argparse.Namespace
            The parsed arguments for the ``identify-matrices`` sub-command.
    """
    controllers = execute_get_controllers(cli_args)

    for controller in controllers:
        controller.identify(
            skip_clear=cli_args.skip_clear,
            duration=float(cli_args.runtime),
            cycles=int(cli_args.cycle_count),
        )


def main(cli_args=ARGUMENTS):
    """
    Parses and handles command-line arguments, registering specific subcommands
    and executing associated functions.

    This function sets up a command-line interface (CLI) parser, registers a
    specific subcommand (`scroll-text`), and associates a function (`scroll_text_command`)
    with this subcommand. After parsing the arguments, it executes the appropriate
    function based on the parsed subcommand.

    Parameters:
        cli_args (Optional[Arguments]):
            An object containing the command-line parser and associated
            subcommand configurations. It must have attributes `scroll_parser`
            and a callable `parse` function. (Defaults to `ARGUMENTS`)
    """
    parser_bindings = (
        ('scroll_parser', 'Scroll text command parser was not initialized.', scroll_text_command),
        ('identify_parser', 'Identify matrices command parser was not initialized.', identify_matrices_command),
        ('display_parser', 'Display text command parser was not initialized.', display_text_command),
    )

    for attr_name, error_message, handler in parser_bindings:
        parser = getattr(cli_args, attr_name)
        if parser is None:
            raise RuntimeError(error_message)
        parser.set_defaults(func=handler)

    # Parse command-line arguments;
    parsed = cli_args.parse()

    # Run the function associated with the parsed command;
    parsed.func(parsed)


if __name__ == '__main__':
    main()


