from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments import Arguments


ARGUMENTS = Arguments()
"""
The object that holds the command-line arguments. This is a subclass of `argparse.ArgumentParser`
"""


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

    filtered = _filter_controllers_by_side(controllers, cli_args)

    if not filtered:
        raise SystemExit(f'No LED matrices matched the requested selection ({_describe_selection(cli_args)}).')

    return filtered


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

    # ToDo:
    #    - Add ability to control the scroll speed.
    #    - Add ability to loop message scrolling;
    #        - Indefinitely, or;
    #        - A specified number of times, or;
    #        - A specified duration in seconds.

    matrix = controllers[0]

    matrix.scroll_text(cli_args.input, direction=DIRECTION_MAP[cli_args.direction.strip().lower()])


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
    # Grab the subparser for the `scroll-text` command;
    scroll_parser   = cli_args.scroll_parser
    identify_parser = cli_args.identify_parser

    # Register `scroll_text_command` as the function to run if the
    # `scroll-text` command is called;
    if scroll_parser is None:
        raise RuntimeError('Scroll text command parser was not initialized.')
    scroll_parser.set_defaults(func=scroll_text_command)

    if identify_parser is None:
        raise RuntimeError('Identify matrices command parser was not initialized.')
    identify_parser.set_defaults(func=identify_matrices_command)

    # Parse command-line arguments;
    parsed = cli_args.parse()

    # Run the function associated with the parsed command;
    parsed.func(parsed)


if __name__ == '__main__':
    main()


