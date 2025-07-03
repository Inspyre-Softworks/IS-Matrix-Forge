import json
from is_matrix_forge.led_matrix.controller import LEDMatrixController, get_controllers
from is_matrix_forge.led_matrix.display.text.scroller import scroll_text_on_multiple_matrices
from platformdirs import PlatformDirs


PLATFORM_DIRS = PlatformDirs("IS-Matrix-Forge", "Inspyre Softworks")


APP_DIR = PLATFORM_DIRS.user_data_path
MEMORY_FILE = APP_DIR / 'memory.ini'


MEMORY_FILE_TEMPLATE = {
    'first_run': True
}

first_run = False

APP_DIR.mkdir(parents=True, exist_ok=True)

if not MEMORY_FILE.exists():
    MEMORY_FILE.write_text(json.dumps(MEMORY_FILE_TEMPLATE))


def get_first_run():
    global first_run
    with open(MEMORY_FILE, 'r') as f:
        memory = json.load(f)
    first_run = memory['first_run']
    return first_run


def set_first_run():
    global first_run
    with open(MEMORY_FILE, 'r') as f:
        memory = json.load(f)

    memory['first_run'] = False

    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f)


def process_first_run():
    global first_run
    fr = get_first_run()

    if fr:
        controllers = get_controllers(threaded=True)
        scroll_text_on_multiple_matrices(controllers, 'Welcome!', threaded=True)

    set_first_run()


process_first_run()


