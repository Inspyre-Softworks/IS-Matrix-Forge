from typing import List
import json
import importlib.resources

from is_matrix_forge.assets.font_map.base import FontMap
from is_matrix_forge.assets.digit_map import DIGITS


# Load the default font map shipped with the package using importlib.resources
with importlib.resources.open_text("is_matrix_forge.assets", "char_map.json", encoding="utf-8") as f:
    _FONT_DATA = json.load(f)
FONT_MAP = FontMap(font_map=_FONT_DATA)


def convert_font(ch: str) -> List[int]:
    """Return the 5x6 glyph list for a single character."""
    return FONT_MAP.lookup(ch, kind="character")


def convert_symbol(symbol: str) -> List[int]:
    """Return the glyph list for a named symbol."""
    return FONT_MAP.lookup(symbol, kind="symbol")
