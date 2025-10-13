from typing import Optional

from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments import Arguments


ARGUMENTS = Arguments()
"""
The object that holds the command-line arguments. This is a subclass of `argparse.ArgumentParser`
"""


def execute_get_controllers():
    """
    Invokes the command to get the controller objects for each available LED matrix.

    Returns:
        List[LEDMatrixController]:
            A list of controller objects, each representing an available LED matrix.
    """
    from is_matrix_forge.led_matrix.controller import get_controllers
    return get_controllers(
        threaded                 = True,
        skip_all_init_animations = True,
        clear_on_init            = True
    )


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
    controllers = execute_get_controllers()

    # ToDo:
    #    - Add ability to control which matrix the message is scrolled on if more than one is available.
    #    - Add ability to control the scroll speed.
    #    - Add ability to loop message scrolling;
    #        - Indefinitely, or;
    #        - A specified number of times, or;
    #        - A specified duration in seconds.

    matrix = controllers[0]

    matrix.scroll_text(cli_args.input, direction=DIRECTION_MAP[cli_args.direction.strip().lower()])


def identify_matrices_command(which: Optional[str]):
    """
    Runs the identification routine on each found controller (or one, if configured to do so).

    Returns:
        None
    """
    from ..identify_matrices import main as identify_matrices
    controllers = execute_get_controllers()

    for controller in controllers:
        controller.identify()


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
    scroll_parser.set_defaults(func=scroll_text_command)

    # Parse command-line arguments;
    parsed = cli_args.parse()

    # Run the function associated with the parsed command;
    parsed.func(parsed)


if __name__ == '__main__':
    main()


