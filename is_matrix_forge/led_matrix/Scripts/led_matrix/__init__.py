import threading
from collections.abc import Callable, Iterable

from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments import Arguments
from is_matrix_forge.led_matrix.Scripts.led_matrix.guards import run_with_guard


ARGUMENTS = Arguments()


def _normalize_side(value):
    if isinstance(value, str):
        return value.strip().lower()
    return None


def _desired_side(cli_args):
    if cli_args is None:
        return None

    if getattr(cli_args, 'only_left', False):
        return 'left'

    if getattr(cli_args, 'only_right', False):
        return 'right'

    return None


def _controller_side(controller):
    side = getattr(controller, 'side_of_keyboard', None)
    normalized = _normalize_side(side)

    if normalized is not None:
        return normalized

    location = getattr(controller, 'location', None)

    if isinstance(location, dict):
        return _normalize_side(location.get('side'))

    if isinstance(location, str):
        from is_matrix_forge.led_matrix.constants import SLOT_MAP

        return _normalize_side(SLOT_MAP.get(location, {}).get('side'))

    return None


def _filter_controllers_by_side(controllers, cli_args):
    """Return the controllers that match the requested keyboard side."""

    desired = _desired_side(cli_args)

    if desired is None:
        return list(controllers)

    return [
        controller for controller in controllers
        if _controller_side(controller) == desired
    ]


def _describe_selection(cli_args):
    desired = _desired_side(cli_args)

    if desired == 'left':
        return 'the leftmost LED matrix'

    if desired == 'right':
        return 'the rightmost LED matrix'

    return 'any LED matrix'


def _run_operation(controllers: Iterable, operation: Callable, *, concurrent: bool) -> None:
    """Run an operation against one or more controllers, optionally in parallel."""

    if concurrent and len(controllers) > 1:
        threads = []

        for controller in controllers:
            thread = threading.Thread(target=operation, args=(controller,), daemon=True)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()
        return

    for controller in controllers:
        operation(controller)


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

    sequential = getattr(cli_args, 'sequential', False) and len(controllers) > 1

    concurrent = not sequential

    def activator(devices, _stop_event):
        def operation(controller):
            controller.keep_alive = True
            controller.scroll_text(text, direction=direction)

        _run_operation(devices, operation, concurrent=concurrent)

    def invoke(targets, index=None):
        run_with_guard(
            targets,
            run_for=None,
            clear_after=False,
            activator=activator,
            thread_name='scroll-text-guard' if index is None else f'scroll-text-guard-{index}',
        )

    if sequential:
        for index, controller in enumerate(controllers, start=1):
            invoke([controller], index)
    else:
        invoke(controllers)


def display_text_command(cli_args):
    """Display static text on the selected LED matrices until interrupted."""
    controllers = execute_get_controllers(cli_args)

    clear_after = not cli_args.skip_clear
    sequential = getattr(cli_args, 'sequential', False) and len(controllers) > 1

    if sequential and cli_args.run_for is None:
        raise SystemExit('--sequential requires --run-for when multiple matrices are targeted.')

    wait_for_interrupt = cli_args.run_for is None
    text = cli_args.text

    concurrent = not sequential

    def activator(devices, _stop_event):
        def operation(controller):
            controller.keep_alive = True
            controller.show_text(text)

        _run_operation(devices, operation, concurrent=concurrent)

    def invoke(targets, index=None):
        run_with_guard(
            targets,
            run_for=cli_args.run_for,
            clear_after=clear_after,
            activator=activator,
            thread_name='display-text-guard' if index is None else f'display-text-guard-{index}',
            wait_for_interrupt=wait_for_interrupt,
        )

    if sequential:
        for index, controller in enumerate(controllers, start=1):
            invoke([controller], index)
    else:
        invoke(controllers)


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


