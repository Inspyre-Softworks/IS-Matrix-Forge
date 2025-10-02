from typing import Dict, Any

from importlib.resources import files
import json

from .models.glyph import Glyph


def load_builtin_char_map() -> Dict[str, Glyph]:
    resource = files('is_matrix_forge.assets').joinpath('char_map.json')
    if not resource.is_file():
        raise FileNotFoundError('char_map.json missing from is_matrix_forge.assets package data')
    data = json.loads(resource.read_text())

    return dict(data)


def has_key_ignore_case(
        d: Dict[str, Any],
        key: str
) -> bool:
    kf = key.casefold()

    return any(k.casefold() == kf for k in d)


def get_ignore_case(
        d: Dict[str, Any],
        key: str,
        default=None
):
    kf = key.casefold()

    return next((v for k, v in d.items() if k.casefold() == kf), default)

