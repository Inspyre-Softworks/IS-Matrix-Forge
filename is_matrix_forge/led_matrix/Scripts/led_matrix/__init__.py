from is_matrix_forge.led_matrix.Scripts.led_matrix.arguments import Arguments
from is_matrix_forge import get_controllers
from .arguments.commands.scroll_text import DIRECTION_MAP


ARGUMENTS = Arguments()

CONTROLLERS = get_controllers(
    threaded=True,
    skip_all_init_animations=True,
    clear_on_init=True
)


def scroll_text_command(cli_args=ARGUMENTS):
    global CONTROLLERS

    matrix = CONTROLLERS[0]
    print(cli_args.input)

    matrix.scroll_text(cli_args.input, direction=DIRECTION_MAP[cli_args.direction.strip().lower()])


def main(cli_args=ARGUMENTS):
    scroll_parser = cli_args.scroll_parser
    scroll_parser.set_defaults(func=scroll_text_command)
    parsed = cli_args.parse()
    parsed.func(parsed)


if __name__ == '__main__':
    main()


