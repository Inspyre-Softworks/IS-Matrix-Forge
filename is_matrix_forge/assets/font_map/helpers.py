from typing import Dict, Any

from importlib.resources import files
import json

from .models.glyph import Glyph


def load_builtin_char_map() -> Dict[str, Glyph]:
    data = json.loads(files('is_matrix_forge.assets').joinpath('char_map.json').read_text())

    return {k: v for k, v in data.items()}


def has_key_ignore_case(
        d: Dict[str, Any],
        key: str
) -> bool:
    kf = key.casefold()

    return any(k.casefold() == kf for k in d.keys())


def get_ignore_case(
        d: Dict[str, Any],
        key: str,
        default=None
):
    kf = key.casefold()

    for k, v in d.items():
        if k.casefold() == kf:
            return v

    return default

