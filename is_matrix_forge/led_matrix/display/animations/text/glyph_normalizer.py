"""Helpers for normalizing font glyph data used by :mod:`text_scroller`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List


GlyphRows = List[List[int]]


@dataclass(slots=True)
class GlyphNormalizer:
    """Normalize glyph objects into a row-major 0/1 matrix."""

    matrix_width: int
    matrix_height: int

    def rows_to_cols(self, rows: GlyphRows) -> GlyphRows:
        if not rows:
            return []
        height = len(rows)
        width = len(rows[0])
        return [[rows[r][c] for r in range(height)] for c in range(width)]

    def _binary_flat_to_rows(self, flat: List[int]) -> GlyphRows:
        if not flat:
            return [[0]]

        if any(v not in (0, 1) for v in flat):
            raise ValueError('Flat glyph list must contain only 0/1 values')

        total = len(flat)
        max_width = min(self.matrix_width, total)
        candidates: List[tuple[int, int]] = []
        for width in range(1, max_width + 1):
            if total % width:
                continue
            height = total // width
            if height <= self.matrix_height:
                candidates.append((width, height))

        if not candidates:
            return [flat[:max_width]]

        preferred_widths = [5, 4, 6, 7, 8, 9, 3, 2, 1]
        chosen: tuple[int, int] | None = None
        for pref in preferred_widths:
            for width, height in candidates:
                if width == pref:
                    chosen = (width, height)
                    break
            if chosen:
                break

        if chosen is None:
            chosen = max(candidates, key=lambda wh: (wh[0], wh[1]))

        width, height = chosen
        rows: GlyphRows = []
        for r in range(height):
            start = r * width
            rows.append(flat[start:start + width])
        return rows

    def _cols_mask_to_rows(self, cols: List[int], *, height: int | None = None) -> GlyphRows:
        if not cols:
            return [[0]]
        if height is None:
            height = max(1, max(c.bit_length() for c in cols))

        out: GlyphRows = [
            [(c >> r) & 1 for c in cols] for r in range(height - 1, -1, -1)
        ]
        return out

    def normalize(self, glyph: Any) -> GlyphRows:
        if isinstance(glyph, list) and glyph and isinstance(glyph[0], list):
            return glyph

        if isinstance(glyph, list) and glyph and isinstance(glyph[0], int):
            if all(isinstance(v, int) and v in (0, 1) for v in glyph):
                return self._binary_flat_to_rows(glyph)
            return self._cols_mask_to_rows(glyph)

        if isinstance(glyph, list) and glyph and isinstance(glyph[0], str):
            return [[1 if ch == '1' else 0 for ch in row] for row in glyph]

        if hasattr(glyph, 'rows'):
            rows = getattr(glyph, 'rows')
            if isinstance(rows, list) and rows and isinstance(rows[0], list):
                return rows
        if hasattr(glyph, 'grid'):
            grid = getattr(glyph, 'grid')
            if isinstance(grid, list) and grid and isinstance(grid[0], list):
                return grid
        if hasattr(glyph, 'to_rows'):
            rows = glyph.to_rows()  # type: ignore[attr-defined]
            if isinstance(rows, list) and rows and isinstance(rows[0], list):
                return rows
        if hasattr(glyph, 'cols'):
            cols = getattr(glyph, 'cols')
            if isinstance(cols, list) and cols and isinstance(cols[0], int):
                height = getattr(glyph, 'height', None)
                return self._cols_mask_to_rows(cols, height=height)

        if glyph in (None, 0, []):
            return [[0]]

        raise TypeError(f'Unsupported glyph format: {type(glyph)!r}')
