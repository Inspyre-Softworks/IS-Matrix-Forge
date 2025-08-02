import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from inspyre_toolbox.syntactic_sweets.classes.decorators import validate_type


class FontMap:
    """
    FontMap allows lookup of character and symbol patterns from a JSON-based font map.
    """
    DEFAULT_FALLBACK_CHAR = '?'

    def __init__(
        self,
        font_map: Optional[Dict[str, Dict[str, List[int]]]] = None,
        characters_key: str = 'characters',
        symbols_key: str = 'symbols',
        case_sensitive: bool = False,
        fallback_char: Optional[str] = None
    ):
        """
        Initialize a FontMap instance.

        Parameters:
            font_map: Raw font map dict loaded from JSON (or None to load from JSON file).
            characters_key: Top-level key for character definitions.
            symbols_key: Top-level key for symbol definitions.
            case_sensitive: Toggle case-sensitive lookup.
            fallback_char: Character to use when lookup fails.
        """
        # Lazy-load from JSON if not provided
        if font_map is None:
            map_path = Path(__file__).parent / 'font_map.json'
            font_map = json.load(open(map_path))

        self._map = font_map
        self._characters_key = characters_key
        self._symbols_key = symbols_key
        self._case_sensitive = case_sensitive
        self._fallback_char = fallback_char or self.DEFAULT_FALLBACK_CHAR

    @property
    def character_map(self) -> Dict[str, List[int]]:
        return self._map[self._characters_key]

    @property
    def symbol_map(self) -> Dict[str, List[int]]:
        return self._map[self._symbols_key]

    @property
    def characters(self) -> List[str]:
        return list(self.character_map.keys())

    @property
    def symbols(self) -> List[str]:
        return list(self.symbol_map.keys())

    @property
    def fallback_char(self) -> str:
        return self._fallback_char

    @fallback_char.setter
    def fallback_char(self, new: str):
        if not isinstance(new, str) or len(new) != 1:
            raise ValueError('fallback_char must be a single character string')
        if new not in self.characters + self.symbols:
            raise ValueError(f'{new!r} not found in font map')
        self._fallback_char = new

    @property
    def is_case_sensitive(self) -> bool:
        return self._case_sensitive

    @validate_type(bool)
    @is_case_sensitive.setter
    def is_case_sensitive(self, new: bool):
        self._case_sensitive = new

    def __contains__(self, key: str) -> bool:
        key_norm = self._normalize_key(key)
        return key_norm in self.character_map or key_norm in self.symbol_map

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(case_sensitive={self._case_sensitive}, "
            f"fallback_char={self._fallback_char!r})"
        )

    def lookup(self, key: str, kind: Optional[str] = None) -> List[int]:
        """
        Lookup a character or symbol. If kind is 'character' or 'symbol', force that map.
        """
        key_norm = self._normalize_key(key)
        if kind == 'symbol':
            return self._lookup_map(self.symbol_map, key_norm)
        if kind in ('char', 'character'):
            return self._lookup_map(self.character_map, key_norm)

        # Try characters first, then symbols
        try:
            return self._lookup_map(self.character_map, key_norm)
        except KeyError:
            return self._lookup_map(self.symbol_map, key_norm)

    def reload(self, font_map: Union[str, Path, Dict]):
        """
        Reloads font map from a file path or dict.
        """
        if isinstance(font_map, (str, Path)):
            font_map = json.load(open(font_map))
        self._map = font_map

    def _normalize_key(self, key: str) -> str:
        return key if self._case_sensitive else key.upper()

    def _lookup_map(self, mapping: Dict[str, List[int]], key: str) -> List[int]:
        if key not in mapping:
            key = self._fallback_char
        return mapping[key]
