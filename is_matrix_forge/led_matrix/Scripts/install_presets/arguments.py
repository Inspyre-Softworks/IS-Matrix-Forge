"""
Author: 
    Inspyre Softworks

Project:
    led-matrix-battery

File: 
    is_matrix_forge/led_matrix/Scripts/install_presets/arguments.py

Description:
    Holds the Arguments class for the command-line arguments for the preset
    installer.
"""
from argparse import ArgumentParser
from is_matrix_forge.log_engine import LOG_LEVELS
from is_matrix_forge.led_matrix.constants import APP_DIRS
from is_matrix_forge.common.helpers.github_api import REPO_PRESETS_URL


class Arguments(ArgumentParser):

    def __init__(self, *args, **kwargs):
        super().__init__(
            'IS-Matrix-Forge:install_presets',
            description='Download and install premade LED matrix grid design patterns from GitHub.',
        )
        self.__parsed = None

        self.__build()

    @property
    def parsed(self):
        """
        Returns the parsed command-line arguments.
        """
        if self.__parsed is None:
            self.parse()

        return self.__parsed

    def __build(self):
        """
        Build the command-line arguments.
        """
        # Add the `URL` argument
        self.add_argument(
            '--url',
            help='GitHub API URL to download presets from.',
            default=REPO_PRESETS_URL,
            action='store'
        )

        # Add the `app-dir` argument
        self.add_argument(
            '--app-dir',
            help='The directory in which this app can save its files.',
            default=APP_DIRS.user_data_path,
            action='store'
        )

        # Add the `overwrite` argument.
        self.add_argument(
            '--overwrite',
            help='Overwrite existing preset files to be replaced.',
            action='store_true',

        )

        # Add the `no-progress` argument.
        self.add_argument(
            '--no-progress',
            help='Disable progress bars.',
            action='store_true'
        )

    def parse(self):
        """
        Parse the command-line arguments.

        Note:
            Once this method is run, it will define `Arguments.parsed`.
        """
        self.__parsed = self.parse_args()
