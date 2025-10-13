# =============================================================================
# Author      : Taylor-Jayde Blackstone / Inspyre Softworks
# Project     : IS-Matrix-Forge
# File        : is_matrix_forge/assets/font_map/builders.py
#
# Description :
#   Adapter/builder for turning flat 5x6 (length-30) 0/1 glyph lists into
#   a raw map suitable for FontMap: {'characters': {...}, 'symbols': {...}}.
#   Handles validation, reshaping to row-major 2D lists, and optional aliases.
#
# Dependencies:
#   - is_matrix_forge/assets/font_map/models/glyph.py (Glyph type)
#   - is_matrix_forge/assets/font_map/base.py (FontMap)
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, MutableMapping, Sequence, Tuple

from .models.glyph import Glyph
from .base import FontMap


def _to_rows(flat: Sequence[int], width: int, height: int) -> Glyph:
    """
    Convert a flat 0/1 list into a row-major 2D structure that matches the Glyph type.

    Parameters
    ----------
    flat :
        Flat sequence of ints (0/1). Expected length == width * height.
    width :
        Glyph width (columns).
    height :
        Glyph height (rows).

    Returns
    -------
    Glyph
        Project Glyph value (list of lists of ints).
    """
    if len(flat) != width * height:
        raise ValueError(f'Glyph length {len(flat)} != {width*height} (expected).')
    if any(px not in (0, 1) for px in flat):
        raise ValueError('Glyph data must be 0/1.')
    return [list(flat[r * width:(r + 1) * width]) for r in range(height)]


@dataclass(slots=True)
class FontMapBuilder5x6:
    """
    Build a FontMap from flat 5x6 glyph dictionaries (characters + symbols).

    Parameters
    ----------
    width :
        Glyph width in pixels. Default 5.
    height :
        Glyph height in pixels. Default 6.
    case_sensitive :
        Whether keys should remain case-sensitive in the produced map.
    fallback_char :
        Fallback character key to ensure is present in the output (e.g., '?').

    Notes
    -----
    - Input dicts should be {str: List[int]} with length-30 lists.
    - Aliases are additional keys pointing at an existing glyph key.
    """
    width: int = 5
    height: int = 6
    case_sensitive: bool = False
    fallback_char: str = '?'
    _chars: MutableMapping[str, Glyph] = field(default_factory=dict, init=False)
    _syms: MutableMapping[str, Glyph] = field(default_factory=dict, init=False)

    # --- Registration --------------------------------------------------------

    def add_char_map(self, mapping: Mapping[str, Sequence[int]]) -> 'FontMapBuilder5x6':
        """Register many character glyphs from a flat 0/1 list mapping."""
        for k, v in mapping.items():
            key = k if self.case_sensitive else str(k).upper()
            self._chars[key] = _to_rows(v, self.width, self.height)
        return self

    def add_symbol_map(self, mapping: Mapping[str, Sequence[int]]) -> 'FontMapBuilder5x6':
        """Register many symbol glyphs from a flat 0/1 list mapping."""
        for k, v in mapping.items():
            key = k if self.case_sensitive else (k if len(k) != 1 else k.upper())
            self._syms[key] = _to_rows(v, self.width, self.height)
        return self

    def add_aliases(self, aliases: Mapping[str, str]) -> 'FontMapBuilder5x6':
        """
        Add alias keys that point to existing glyphs.

        Example:
            builder.add_aliases({'°C': 'degC', '°F': 'degF'})
        """
        for alias, target in aliases.items():
            # Try symbols first, then characters
            if target in self._syms:
                self._syms[alias] = self._syms[target]
            elif target in self._chars:
                self._syms[alias] = self._chars[target]
            else:
                tnorm = target if self.case_sensitive else target.upper()
                if tnorm in self._chars:
                    self._syms[alias] = self._chars[tnorm]
                elif tnorm in self._syms:
                    self._syms[alias] = self._syms[tnorm]
                else:
                    raise KeyError(f'Alias target {target!r} not found in current maps.')
        return self

    # --- Output --------------------------------------------------------------

    def build_raw(self) -> Dict[str, Dict[str, Glyph]]:
        """Produce a raw map suitable for FontMap(font_map=RAW)."""
        return {'characters': dict(self._chars), 'symbols': dict(self._syms)}

    def build_font_map(self) -> FontMap:
        """Construct and return a FontMap from the accumulated maps."""
        raw = self.build_raw()
        return FontMap(
            font_map=raw,
            characters_key='characters',
            symbols_key='symbols',
            case_sensitive=self.case_sensitive,
            fallback_char=self.fallback_char,
        )
