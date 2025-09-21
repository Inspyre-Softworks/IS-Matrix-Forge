from argparse import ArgumentParser
from is_matrix_forge.log_engine import LOG_LEVELS
from is_matrix_forge.led_matrix.constants import APP_DIRS


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
        self.__building = False
        self.__built    = False
        self.__parsed   = None
        self.__scroll_parser = None
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
    def scroll_parser(self):
        return self.__scroll_parser

    def __build_scroll_text(self):
        from .commands.scroll_text import register_command
        self.__scroll_parser = register_command(self)

    def __build(self):
        self.__building = True

        self.__build_scroll_text()

        self.__building = False
        self.__built    = True

    def parse(self):
        if not self.built:
            raise RuntimeError('Arguments not yet built. Try calling `Arguments().build`!')

        if not self.__parsed:
            self.__parsed = self.parse_args()

        return self.__parsed
