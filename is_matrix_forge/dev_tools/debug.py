from pathlib import Path
from platformdirs import PlatformDirs
from easy_exit_calls import ExitCallHandler
from is_matrix_forge.log_engine import ROOT_LOGGER as PARENT_LOGGER

MOD_LOGGER = PARENT_LOGGER.get_child('dev_tools.debug')

DEBUG_MODE_KEYFILE_NAME = 'marauder.map'

ECH: ExitCallHandler

PLATFORM_DIRS = PlatformDirs('IS-Matrix-Forge', 'Inspyre Softworks')


def get_debug_mode_keyfile_path():
    return PLATFORM_DIRS.user_data_path


MARAUDER_FILE_PATH = get_debug_mode_keyfile_path()


def create_marauders_map(mm_path=MARAUDER_FILE_PATH):
    log = MOD_LOGGER.get_child('create_marauders_map')
    mm_path = Path(mm_path).expanduser().resolve()
    log.debug(f'Creating Marauder\'s Map at {mm_path}')

    if not mm_path.parent.exists():
        log.debug(f'Creating parent directory for Marauder\'s Map: {mm_path.parent}')
        mm_path.parent.mkdir(parents=True, exist_ok=True)

    with open(mm_path, 'w') as f:
        f.write('Mooney, Wormtail, Padfoot, and Prongs are proud to present the Marauder\'s Map.')

    log.debug(f'Marauder\'s Map created at {mm_path}')


def disable_debug_mode(mm_file_path=MARAUDER_FILE_PATH):
    log = MOD_LOGGER.get_child('disable_debug_mode')
    mm_file_path = Path(mm_file_path).expanduser().resolve()
    log.debug(f'Writing magic words to Marauder\'s Map at {mm_file_path}')

    if not mm_file_path.exists():
        log.warning(f'Marauder\'s Map file does not exist: {mm_file_path}. (No debug mode to disable)')
        raise RuntimeError(f'Marauder\'s Map file does not exist: {mm_file_path}. (No debug mode to disable)')

    with open(MARAUDER_FILE_PATH, 'w') as f:
        f.write('Mischief Managed.')
    log.debug(f'Magic words written to Marauder\'s Map at {mm_file_path}')

    if 'ECH' in globals() and globals()['ECH'].function_registered(disable_debug_mode):
        log.debug(f'Found ExitCallHandler instance with registered function: {disable_debug_mode}. Unregistering it.')
        globals()['ECH'].unregister_handler(disable_debug_mode)
        log.debug('Unregistered ExitCallHandler instance with registered function: {disable_debug_mode}.')


def enable_debug_mode(
        mm_file_path=MARAUDER_FILE_PATH,
        disable_on_exit=False,
):
    mm_file_path = Path(mm_file_path).expanduser().resolve()

    if not mm_file_path.exists():
        create_marauders_map(mm_file_path)

    with open(MARAUDER_FILE_PATH, 'w') as f:
        f.write('I solemnly swear that I am up to no good.')

    if disable_on_exit:
        from easy_exit_calls import ExitCallHandler
        global ECH
        ech = ExitCallHandler()
        ech.register_handler(disable_debug_mode, mm_file_path)


def is_debug_mode(portkey_file_path=MARAUDER_FILE_PATH):
    try:
        with open(portkey_file_path, 'r') as f:
            # Check if the file contains the correct content
            content = f.read()
            return content.strip() == 'I solemnly swear that I am up to no good.'
    except FileNotFoundError:
        return False
