import json
from pathlib import Path

from platformdirs import PlatformDirs


def pytest_configure():
    dirs = PlatformDirs("IS-Matrix-Forge", "Inspyre Softworks")
    mem_file = Path(dirs.user_data_path) / "memory.ini"
    mem_file.parent.mkdir(parents=True, exist_ok=True)
    mem_file.write_text(json.dumps({"first_run": False}))

