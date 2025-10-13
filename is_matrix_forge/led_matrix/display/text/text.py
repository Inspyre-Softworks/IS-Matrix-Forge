# =============================================================================
# Author      : Taylor-Jayde Blackstone / Inspyre Softworks
# Project     : IS-Matrix-Forge
# File        : is_matrix_forge/led_matrix/display/text.py
#
# Description :
#   Class-based integration for showing short text/symbol stacks on the
#   9x34 matrix using a 5x6 bitmap font (up to 5 items stacked vertically,
#   spaced 7 rows apart). Supports two backends:
#     1) Legacy driver: pack 9*34 bits into 39 bytes and send CommandVals.Draw
#     2) Grid backend: build a 9x34 grid and call render_matrix()
#
#   Provides convenience functions that mirror the old procedural API:
#     - show_string(dev, s)
#     - show_symbols(dev, symbols)
#     - show_font(dev, font_items)
#
#   Under the hood, uses FontMap (or a builder) so you can feed in the
#   dicts from convert_font() / convert_symbol() without modification.
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from aliaser import alias, Aliases

# Project imports
from is_matrix_forge.led_matrix.display.helpers import render_matrix
from is_matrix_forge.led_matrix.display.grid import Grid
from is_matrix_forge.led_matrix.display.grid.helpers import generate_blank_grid

# Font infra (your existing classes)
from is_matrix_forge.assets.font_map.base import FontMap
from is_matrix_forge.assets.font_map.builders import FontMapBuilder5x6

# Optional legacy driver imports; guarded so the module works without them.
try:
    from is_matrix_forge.led_matrix.hardware.driver import send_command, CommandVals  # type: ignore
    _HAS_DRIVER = True
except Exception:  # pragma: no cover - best-effort import
    send_command = None  # type: ignore
    CommandVals = None   # type: ignore
    _HAS_DRIVER = False


Glyph = List[List[int]]  # 5 rows x 6? Actually width=5, height=6 => rows:6, cols:5 (row-major)


@dataclass(slots=True)
class RenderConfig:
    """
    Configuration for 5x6 text rendering.

    Parameters
    ----------
    matrix_cols :
        Total matrix width (columns). Default 9.
    matrix_rows :
        Total matrix height (rows). Default 34.
    glyph_width :
        Glyph width in pixels. Default 5.
    glyph_height :
        Glyph height in pixels. Default 6.
    vertical_spacing :
        Rows between the *starts* of stacked glyphs. Default 7 (6 rows glyph + 1 spacer).
    x_offset :
        Starting x column for the glyph block. Default 2 (centers 5 cols within 9).
    max_items :
        Maximum stacked glyphs. Default 5 (fits 5*7 = 35 rows -> last row is outside; we draw 5 with 6 px height).
    use_driver_pack :
        When True and driver is available, pack to 39 bytes and call send_command.
        Otherwise, render via Grid/render_matrix.
    """
    matrix_cols: int = 9
    matrix_rows: int = 34
    glyph_width: int = 5
    glyph_height: int = 6
    vertical_spacing: int = 7
    x_offset: int = 2
    max_items: int = 5
    use_driver_pack: bool = True

    @property
    def packed_buffer_len(self) -> int:
        # ceil(9*34 / 8) = 39
        total_bits = self.matrix_cols * self.matrix_rows
        return (total_bits + 7) // 8


class TextRenderer5x6(Aliases):
    """
    Renderer that composes up to five 5x6 glyphs vertically on a 9x34 matrix.

    You can create with an existing FontMap, or pass raw dicts from convert_font()
    / convert_symbol() via the builder helpers.

    Example
    -------
    >>> renderer = TextRenderer5x6.from_flat_dicts(FONT, SYMBOLS)
    >>> renderer.show_string(dev, 'HELLO')
    >>> renderer.show_symbols(dev, [':)', 'degC', 'sun'])
    """

    def __init__(self, font_map: FontMap, config: Optional[RenderConfig] = None):
        self._font_map = font_map
        self._cfg = config or RenderConfig()

    # --------- Construction helpers --------- #

    @classmethod
    def from_flat_dicts(
        cls,
        chars_dict: Mapping[str, Sequence[int]],
        symbols_dict: Mapping[str, Sequence[int]],
        *,
        case_sensitive: bool = False,
        fallback_char: str = '?',
        config: Optional[RenderConfig] = None,
        aliases: Optional[Mapping[str, str]] = None,
    ) -> 'TextRenderer5x6':
        """
        Build a TextRenderer5x6 from raw {str: flat_01_list_len_30} dicts.

        Parameters
        ----------
        chars_dict :
            Mapping of character -> 30-length 0/1 flat list (your convert_font()).
        symbols_dict :
            Mapping of token -> 30-length 0/1 flat list (your convert_symbol()).
        case_sensitive :
            Whether FontMap keys are case sensitive.
        fallback_char :
            Fallback glyph key (e.g., '?').
        config :
            Optional RenderConfig override.
        aliases :
            Optional {alias: target_key} mapping (e.g., {'°C': 'degC'}).
        """
        builder = FontMapBuilder5x6(
            case_sensitive=case_sensitive,
            fallback_char=fallback_char,
        )
        builder.add_char_map(chars_dict).add_symbol_map(symbols_dict)
        if aliases:
            builder.add_aliases(aliases)
        return cls(builder.build_font_map(), config=config)

    # --------- Public API (legacy-compatible) --------- #

    @alias('show_text', 'render_text', 'render_string')
    def show_string(self, dev, s: Union[str, Iterable[str]]) -> None:
        """
        Render a string (first 5 characters) using the character map.
        Mirrors legacy `show_string(dev, s)` semantics.
        """
        from is_matrix_forge.led_matrix.controller import LEDMatrixController

        if isinstance(dev, LEDMatrixController):
            dev.show_text(s)

        text = ''.join(list(str(s))[: self._cfg.max_items])
        glyphs = [self._font_map[ch] for ch in text]



        self._render_glyph_stack(dev, glyphs)

    def show_symbols(self, dev, symbols: Iterable[str]) -> None:
        """
        Render up to five "symbol tokens" (or characters).
        Mirrors legacy `show_symbols(dev, symbols)` behavior.
        """
        glyphs: List[Glyph] = []
        for token in list(symbols)[: self._cfg.max_items]:
            # Try symbols first, then character fallback (same as your legacy logic)
            g = self._font_map.lookup(token, kind='symbol')
            if g is None or not isinstance(g, list):  # extremely defensive; FontMap always returns a Glyph
                g = self._font_map[token]
            glyphs.append(g)
        self._render_glyph_stack(dev, glyphs)

    def show_font_items(self, dev, font_items: Iterable[Glyph]) -> None:
        """
        Render pre-resolved glyphs (each a 6x5 row-major list of 0/1).
        Mirrors legacy `show_font(dev, font_items)` behavior.
        """
        self._render_glyph_stack(dev, list(font_items)[: self._cfg.max_items])

    # --------- Core render path --------- #

    def _render_glyph_stack(self, dev, glyphs: Sequence[Glyph]) -> None:
        if self._cfg.use_driver_pack and _HAS_DRIVER:
            buf = self._pack_glyphs_to_bytes(glyphs)
            send_command(dev, CommandVals.Draw, buf)  # type: ignore[misc]
            return

        # Grid fallback: draw onto a 9x34 grid and render_matrix()
        grid = self._compose_grid(glyphs)
        render_matrix(dev, grid)

    def _coerce_rows(self, glyph):
        """Return rows[6][5] from either a flat 30-length list or a 2D list."""
        if isinstance(glyph, list) and glyph and isinstance(glyph[0], list):
            # already rows
            return glyph
        if isinstance(glyph, list):
            w, h = self._cfg.glyph_width, self._cfg.glyph_height
            if len(glyph) == w * h and all(isinstance(px, int) for px in glyph):
                return [glyph[r * w:(r + 1) * w] for r in range(h)]
        raise TypeError('Glyph must be a 2D row-major list or a flat length-30 list of 0/1.')

    def _pack_glyphs_to_bytes(self, glyphs):
        cfg = self._cfg
        vals = [0x00 for _ in range(cfg.packed_buffer_len)]
        total_bits = cfg.matrix_cols * cfg.matrix_rows
        for digit_i, g in enumerate(glyphs):
            glyph = self._coerce_rows(g)  # <-- important
            offset = digit_i * cfg.vertical_spacing
            for px in range(cfg.glyph_width):
                for py in range(cfg.glyph_height):
                    if glyph[py][px]:
                        i = (cfg.x_offset + px) + (cfg.matrix_cols * (py + offset))
                        if 0 <= i < total_bits:
                            vals[i // 8] |= (1 << (i % 8))
        return vals


    def _compose_grid(self, glyphs):
        """
        Compose glyphs onto the matrix grid, tolerating either 34x9 or 9x34 shape.
        """
        cfg = self._cfg
        grid = generate_blank_grid(width=cfg.matrix_cols, height=cfg.matrix_rows, fill_value=0)

        rows = len(grid)
        cols = len(grid[0]) if rows else 0

        # We want to place into a logical 34(rows) x 9(cols) space.
        # If the actual grid is 9x34, we write transposed: grid[row][col] with row<-gx, col<-gy.
        write_transposed = (rows == cfg.matrix_cols and cols == cfg.matrix_rows)  # i.e., 9x34

        for digit_i, g in enumerate(glyphs):
            glyph = self._coerce_rows(g)
            y_offset = digit_i * cfg.vertical_spacing  # 0,7,14,21,28
            for py in range(cfg.glyph_height):  # 0..5
                gy = y_offset + py  # 0..33 max
                if not (0 <= gy < cfg.matrix_rows):
                    continue
                if write_transposed:
                    # grid is 9x34: rows=9(cols), cols=34(rows)
                    for px in range(cfg.glyph_width):  # 0..4
                        gx = cfg.x_offset + px  # 2..6
                        if 0 <= gx < cfg.matrix_cols and glyph[py][px]:
                            grid[gx][gy] = 1  # swap indices
                else:
                    # grid is 34x9: rows=34, cols=9
                    row = grid[gy]
                    for px in range(cfg.glyph_width):
                        gx = cfg.x_offset + px
                        if 0 <= gx < cfg.matrix_cols and glyph[py][px]:
                            row[gx] = 1
        return grid

# ----------------------------- Legacy-style API ----------------------------- #
# Module-level renderer cache so repeated calls aren't rebuilding maps each time.
_RENDERER: Optional[TextRenderer5x6] = None


def _get_renderer() -> TextRenderer5x6:
    global _RENDERER
    if _RENDERER is None:
        # Default to builtin map if available; otherwise user should construct explicitly.
        # Here we assume load_builtin_char_map() returns a combined map; we wrap via FontMap.
        from is_matrix_forge.assets.font_map.helpers import load_builtin_char_map
        fm = FontMap(font_map=load_builtin_char_map(), case_sensitive=False, fallback_char='?')
        _RENDERER = TextRenderer5x6(fm)
    return _RENDERER


@alias('show_text')
def show_string(dev, s: str) -> None:
    """
    Render a string with up to five letters (legacy-compatible).
    """
    _get_renderer().show_string(dev, s)


def show_symbols(dev, symbols: Iterable[str]) -> None:
    """
    Render a list of up to five symbols (legacy-compatible).
    Accepts letters/numbers or symbol names like 'sun', ':)', 'degC'.
    """
    _get_renderer().show_symbols(dev, symbols)


def show_font(dev, font_items: Iterable[Glyph]) -> None:
    """
    Render up to five 5x6 glyphs already resolved to row-major lists (legacy-compatible).
    """
    _get_renderer().show_font_items(dev, font_items)

