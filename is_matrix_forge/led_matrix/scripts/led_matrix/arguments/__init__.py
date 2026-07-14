from argparse import Action, ArgumentParser
from is_matrix_forge.log_engine import LOG_LEVELS
from is_matrix_forge.led_matrix.constants import APP_DIRS


def build_version_output(*, check_updates: bool = False) -> str:
    from is_matrix_forge.led_matrix.scripts.led_matrix.support import build_version_output as _build_version_output

    return _build_version_output(check_updates=check_updates)


class _VersionAction(Action):
    def __init__(self, option_strings, dest, **kwargs):
        kwargs.setdefault("nargs", 0)
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print(build_version_output(check_updates=False))
        parser.exit()


class _CheckUpdatesAction(Action):
    def __init__(self, option_strings, dest, **kwargs):
        kwargs.setdefault("nargs", 0)
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print(build_version_output(check_updates=True))
        parser.exit()


class Arguments(ArgumentParser):
    def __init__(self, *args, **kwargs):
        prog = kwargs.pop('prog', 'led-matrix')
        description = kwargs.pop('description', 'Use the Framework LED matrices from the command-line.')

        super().__init__(
            'led-matrix',
            description='Use the Framework LED matrices from the command-line.',
            *args,
            **kwargs
        )
        self.__building              = False
        self.__built                 = False
        self.__parsed                = None
        self.__identify_parser       = None
        self.__scroll_parser         = None
        self.__display_parser        = None
        self.__bootloader_parser      = None
        self.__install_presets_parser = None
        self.__scroll_until_parser    = None
        self.__set_presets_dir_parser = None
        self.__show_presets_dir_parser = None
        self.__controller_info_parser = None
        self.__ticket_info_parser = None

        self.add_argument(
            "-V", "--version",
            action=_VersionAction,
            help="Show the installed/source version information and exit.",
        )
        self.add_argument(
            "--check-updates",
            action=_CheckUpdatesAction,
            help="Check PyPI for a newer release and exit.",
        )

        selection_group = self.add_mutually_exclusive_group()
        selection_group.add_argument(
            '-L', '--only-left',
            action='store_true',
            default=False,
            help='Only target the leftmost matrix when executing commands.'
        )
        selection_group.add_argument(
            '-R', '--only-right',
            action='store_true',
            default=False,
            help='Only target the rightmost matrix when executing commands.'
        )

        self.SUBCOMMANDS = self.add_subparsers(
            dest='subcommand',
            required=True,
            help='Available commands: ',
            parser_class=ArgumentParser
        )

        self.__build()

    @property
    def building(self):
        return self.__building

    @property
    def built(self):
        return self.__built

    @property
    def identify_parser(self):
        """
        The command-line argument parser for the 'identify-matrices' command.

        Note:
            This will get a definition when `__build_identify_matrices` is run.

        Returns:
            ArgumentParser:
                The command-line argument parser for the 'identify-matrices' sub-command.
        """
        return self.__identify_parser

    @property
    def scroll_parser(self):
        return self.__scroll_parser

    @property
    def display_parser(self):
        return self.__display_parser

    @property
    def bootloader_parser(self):
        return self.__bootloader_parser

    @property
    def install_presets_parser(self):
        return self.__install_presets_parser

    @property
    def scroll_until_parser(self):
        return self.__scroll_until_parser

    @property
    def set_presets_dir_parser(self):
        return self.__set_presets_dir_parser

    @property
    def show_presets_dir_parser(self):
        return self.__show_presets_dir_parser

    @property
    def controller_info_parser(self):
        return self.__controller_info_parser

    @property
    def ticket_info_parser(self):
        return self.__ticket_info_parser

    def __build_identify_matrices(self):
        from .commands.identify_matrices import register_command
        self.__identify_parser = register_command(self)

    def __build_scroll_text(self):
        from .commands.scroll_text import register_command
        self.__scroll_parser = register_command(self)

    def __build_display_text(self):
        from .commands.display_text import register_command
        self.__display_parser = register_command(self)

    def __build_bootloader(self):
        from .commands.bootloader import register_command
        self.__bootloader_parser = register_command(self)

    def __build_install_presets(self):
        from .commands.install_presets import register_command
        self.__install_presets_parser = register_command(self)

    def __build_scroll_until(self):
        from .commands.scroll_until import register_command
        self.__scroll_until_parser = register_command(self)

    def __build_set_presets_dir(self):
        from .commands.set_presets_dir import register_command
        self.__set_presets_dir_parser = register_command(self)

    def __build_show_presets_dir(self):
        from .commands.show_presets_dir import register_command
        self.__show_presets_dir_parser = register_command(self)

    def __build_controller_info(self):
        from .commands.controller_info import register_command
        self.__controller_info_parser = register_command(self)

    def __build_ticket_info(self):
        from .commands.ticket_info import register_command
        self.__ticket_info_parser = register_command(self)

    def __build(self):
        self.__building = True

        self.__build_identify_matrices()
        self.__build_scroll_text()
        self.__build_display_text()
        self.__build_bootloader()
        self.__build_install_presets()
        self.__build_scroll_until()
        self.__build_set_presets_dir()
        self.__build_show_presets_dir()
        self.__build_controller_info()
        self.__build_ticket_info()

        self.__building = False
        self.__built    = True

    def parse(self):
        if not self.built:
            raise RuntimeError('Arguments not yet built. Try calling `Arguments().build`!')

        if not self.__parsed:
            self.__parsed = self.parse_args()

        return self.__parsed
