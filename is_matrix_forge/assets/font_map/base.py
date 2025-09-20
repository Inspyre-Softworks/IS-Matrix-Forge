"""
Author:
    Inspyre Softworks

Project:
    IS-Matrix-Forge

File:
    ${DIR_PATH}/${FILE_NAME}

Description:
    FontMap: a dict-like facade over character/symbol glyph data with optional
    case-insensitive lookups and a configurable fallback character.
"""

from __future__ import annotations

from collections.abc import Mapping, Iterator
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from inspyre_toolbox.syntactic_sweets.classes import validate_type
from .models.glyph import Glyph
from .helpers import load_builtin_char_map, get_ignore_case, has_key_ignore_case


@dataclass(init=False, slots=True)
class FontMap(Mapping[str, Glyph]):
    """
    FontMap allows lookup of character and symbol patterns as a dict-like mapping.

    Parameters:
        font_map:
            Either:
              - a *combined* map: { 'A': Glyph, '?': Glyph, ... }, or
              - a *raw* map with top-level keys for characters/symbols:
                { 'characters': {...}, 'symbols': {...} }.
            If None, falls back to `load_builtin_char_map()`.
        characters_key:
            Key name used for character definitions when a *raw* map is supplied.
        symbols_key:
            Key name used for symbol definitions when a *raw* map is supplied.
        case_sensitive:
            When False (default), keys are normalized to uppercase.
        fallback_char:
            Glyph to use when a key is missing. Defaults to '?' (or ' ' if '?' not present).

    Properties:
        is_case_sensitive (bool): Current case-sensitivity flag.
        fallback_char (str): Current fallback character.
        characters (list[str]): Keys in the character sub-map (if available).
        symbols (list[str]): Keys in the symbol sub-map (if available).
        character_map (dict[str, Glyph]): Raw character map (best-effort).
        symbol_map (dict[str, Glyph]): Raw symbol map (best-effort).

    Methods:
        lookup(key: str, kind: Optional[str] = None) -> Glyph
            Look up a glyph, optionally forcing 'character' or 'symbol'.
        reload(font_map: dict) -> None
            Replace the underlying map and rebuild indexes.

    Raises:
        ValueError:
            - If `fallback_char` is not a single character.
    Example Usage:
        fm = FontMap()                     # load built-ins
        g_q = fm.get('?')                  # dict-like get
        g_a = fm['A']                      # Mapping access (uses fallback if missing)
        fm.is_case_sensitive = True        # switch mode and reindex
        fm.fallback_char = ' '             # change fallback
        g = fm.lookup('→', kind='symbol')  # force symbol map
    """

    _glyphs: Dict[str, Glyph]
    _raw_map: Optional[Dict[str, Dict[str, Glyph]]]
    _characters_key: str
    _symbols_key: str
    _case_sensitive: bool
    _fallback_char: str

    DEFAULT_FALLBACK_CHAR: str = '?'

    def __init__(
        self,
        font_map: Optional[Dict[str, Any]] = None,
        *,
        characters_key: str = 'characters',
        symbols_key: str = 'symbols',
        case_sensitive: bool = False,
        fallback_char: Optional[str] = None
    ) -> None:
        self._characters_key = characters_key
        self._symbols_key = symbols_key
        self._case_sensitive = case_sensitive
        self._fallback_char = fallback_char or '?'
        self._raw_map = None
        self._glyphs = {}

        # Load data
        if font_map is None:
            # Prefer helper: expected to return a combined {str: Glyph} mapping.
            data = load_builtin_char_map()
            self._ingest_unknown_map(data)
        else:
            self._ingest_unknown_map(font_map)

        self._validate_fallback()

    # ---------- ingestion / normalization ----------

    def _looks_like_raw_map(self, data: Dict[str, Any]) -> bool:
        return (
                isinstance(data, dict)
                and (has_key_ignore_case(data, self._characters_key) or has_key_ignore_case(data, self._symbols_key))
                and isinstance(get_ignore_case(data, self._characters_key, {}), dict)
                and isinstance(get_ignore_case(data, self._symbols_key, {}), dict)
        )

    def _ingest_unknown_map(self, data: Dict[str, Any]) -> None:
        if self._looks_like_raw_map(data):
            chars = dict(get_ignore_case(data, self._characters_key, {}) or {})
            syms = dict(get_ignore_case(data, self._symbols_key, {}) or {})
            self._raw_map = {'characters': chars, 'symbols': syms}
            self._glyphs = {}
            self._merge_into_glyphs(chars)
            self._merge_into_glyphs(syms)
        else:
            self._raw_map = None
            self._ingest_combined_map(data)  # treat as already-flat mapping

    def _ingest_combined_map(self, combined: Dict[str, Glyph]) -> None:
        self._raw_map = None
        self._glyphs = {}
        self._merge_into_glyphs(combined)

    def _merge_into_glyphs(self, mapping: Dict[str, Glyph]) -> None:
        if not mapping:
            return
        if self._case_sensitive:
            for k, v in mapping.items():
                self._glyphs[str(k)] = v
        else:
            for k, v in mapping.items():
                self._glyphs[str(k).upper()] = v

    def _normalize_key(self, key: str) -> str:
        return key if self._case_sensitive else key.upper()

    def _validate_fallback(self) -> None:
        # Ensure fallback exists; prefer '?' then space, otherwise keep as-is but don't explode.
        if self._normalize_key(self._fallback_char) not in self._glyphs:
            if self._normalize_key(' ') in self._glyphs:
                self._fallback_char = ' '

    # ---------- Mapping protocol ----------

    def __getitem__(self, key: str) -> Glyph:
        try:
            return self._glyphs[self._normalize_key(key)]
        except KeyError:
            return self._glyphs[self._normalize_key(self._fallback_char)]

    def __iter__(self) -> Iterator[str]:
        return iter(self._glyphs)

    def __len__(self) -> int:
        return len(self._glyphs)

    # dict-like conveniences
    def get(self, key: str, default: Optional[Glyph] = None) -> Optional[Glyph]:  # type: ignore[override]
        return self._glyphs.get(self._normalize_key(key), default)

    def keys(self) -> Iterable[str]:  # type: ignore[override]
        return self._glyphs.keys()

    def values(self) -> Iterable[Glyph]:  # type: ignore[override]
        return self._glyphs.values()

    def items(self) -> Iterable[tuple[str, Glyph]]:  # type: ignore[override]
        return self._glyphs.items()

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self._normalize_key(key) in self._glyphs

    # ---------- Higher-level API ----------

    def lookup(self, key: str, kind: Optional[str] = None) -> Glyph:
        """
        Lookup a character or symbol by key. If `kind` is provided, force that sub-map.

        Parameters:
            key:
                The character/symbol to look up.
            kind:
                'character'/'char' or 'symbol' to force the specific sub-map. If not provided
                or the raw segmentation is unavailable, falls back to the combined map.

        Returns:
            Glyph for `key`, or the configured fallback glyph if not present.
        """
        if kind is None or self._raw_map is None:
            return self[key]

        k = self._normalize_key(key)
        if kind.lower().startswith('sym'):
            return self._lookup_in(self._raw_map['symbols'], k)
        if kind.lower().startswith('char'):
            return self._lookup_in(self._raw_map['characters'], k)
        return self[key]

    def _lookup_in(self, mapping: Dict[str, Glyph], key: str) -> Glyph:
        if not self._case_sensitive:
            mapping = {str(k).upper(): v for k, v in mapping.items()}
        return mapping.get(key, self._glyphs[self._normalize_key(self._fallback_char)])

    def reload(self, font_map: Dict[str, Any]) -> None:
        """
        Reload the font map (raw or combined) and rebuild indexes.
        """
        self._ingest_unknown_map(font_map)
        self._validate_fallback()

    # ---------- Properties ----------

    @property
    def character_map(self) -> Dict[str, Glyph]:
        if self._raw_map is None:
            return dict(self._glyphs)  # best-effort: treat all as characters
        return dict(self._raw_map['characters'])

    @property
    def symbol_map(self) -> Dict[str, Glyph]:
        if self._raw_map is None:
            return {}
        return dict(self._raw_map['symbols'])

    @property
    def characters(self) -> list[str]:
        return list(self.character_map.keys())

    @property
    def symbols(self) -> list[str]:
        return list(self.symbol_map.keys())

    @property
    def fallback_char(self) -> str:
        return self._fallback_char

    @fallback_char.setter
    def fallback_char(self, new: str) -> None:
        if not isinstance(new, str) or len(new) != 1:
            raise ValueError('fallback_char must be a single character string')
        self._fallback_char = new
        self._validate_fallback()

    @property
    def is_case_sensitive(self) -> bool:
        return self._case_sensitive

    @validate_type(bool)
    @is_case_sensitive.setter
    def is_case_sensitive(self, new: bool) -> None:
        if new is self._case_sensitive:
            return
        # Rebuild normalized key index under the new rule.
        self._case_sensitive = new
        existing = dict(self._glyphs)
        self._glyphs.clear()
        self._merge_into_glyphs(existing)
        self._validate_fallback()

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}('
            f'case_sensitive={self._case_sensitive}, '
            f'fallback_char={self._fallback_char!r}, '
            f'count={len(self)}'
            f')'
        )
