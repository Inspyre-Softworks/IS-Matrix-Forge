from collections.abc import Mapping
from dataclasses import dataclass
from typing import Dict, List, Any

from is_matrix_forge.led_matrix.display.grid.base import MATRIX_WIDTH, MATRIX_HEIGHT
from is_matrix_forge.led_matrix.display.grid import Grid
from is_matrix_forge.led_matrix.display.animations.animation import Animation, Frame


@dataclass(frozen=True)
class TextScrollerConfig:
    """Immutable configuration for the text scroller."""
    text: str
    font_map: Dict[str, List[List[int]]]
    spacing: int = 1
    frame_duration: float = 0.05
    wrap: bool = False  # unused for vertical mode
    direction: str = "horizontal"  # one of: "horizontal", "vertical_up", "vertical_down"


GlyphRows = List[List[int]]


class TextScroller:
    """Generates scrolling‐text Animations in horizontal or vertical directions."""

    VALID_DIRS = {"horizontal", "vertical_up", "vertical_down"}

    def __init__(self, config: TextScrollerConfig):
        self.config = config
        if config.direction not in self.VALID_DIRS:
            raise ValueError(f'Unsupported scroll direction: {config.direction}')

        # Build a rows×cols map regardless of input shapes
        self._rows_map: Dict[str, GlyphRows] = {}
        for k, v in config.font_map.items():
            self._rows_map[k] = self._to_rows_cols(v)

        # sanity sample AFTER normalization
        sample = next(iter(self._rows_map.values()))
        if len(sample) > MATRIX_HEIGHT:
            raise ValueError(f'Font height {len(sample)} > display height {MATRIX_HEIGHT}')

        # -------- normalization helpers --------

    # Add near the top of TextScroller (just a tiny helper)
    def _rows_to_cols(rows: List[List[int]]) -> List[List[int]]:
        if not rows:
            return []
        h, w = len(rows), len(rows[0])
        return [[rows[r][c] for r in range(h)] for c in range(w)]

    def _to_rows_cols(self, glyph: Any) -> GlyphRows:
        # Already rows×cols?
        if isinstance(glyph, list) and glyph and isinstance(glyph[0], list):
            return glyph

        # 1-D list of bit-columns? (e.g., [0b010, 0b111, ...])
        if isinstance(glyph, list) and glyph and isinstance(glyph[0], int):
            return self._cols_mask_to_rows(glyph)

        # String rows like '01010'?
        if isinstance(glyph, list) and glyph and isinstance(glyph[0], str):
            return [[1 if ch == '1' else 0 for ch in row] for row in glyph]

        # Model object? Try common attributes/methods.
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
        if hasattr(glyph, 'cols'):  # columns as bit-masks
            cols = getattr(glyph, 'cols')
            if isinstance(cols, list) and cols and isinstance(cols[0], int):
                # if glyph exposes an explicit height, use it
                h = getattr(glyph, 'height', None)
                return self._cols_mask_to_rows(cols, height=h)

        # Completely blank? Treat as 1-col blank.
        if glyph in (None, 0, []):
            return [[0]]

        raise TypeError(f'Unsupported glyph format: {type(glyph)!r}')

    def _cols_mask_to_rows(self, cols: List[int], *, height: int | None = None) -> GlyphRows:
        if not cols:
            return [[0]]
        if height is None:
            height = max(1, max(c.bit_length() for c in cols))
        # Top row = MSB. Flip the loop if your font expects LSB-at-top.
        out: GlyphRows = []
        for r in range(height - 1, -1, -1):
            out.append([(c >> r) & 1 for c in cols])
        return out

    def generate_animation(self) -> Animation:
        '''
        Build and return the scrolling-text Animation.

        Raises:
            ValueError:
                If any character is missing from the font_map, or if a glyph exceeds
                MATRIX_HEIGHT and fit='error'.
        '''
        # prefer normalized map if present (from __init__), otherwise use config.font_map
        source_map = getattr(self, '_rows_map', self.config.font_map)

        # --- local helpers -------------------------------------------------------
        def to_rows_cols(g):
            # already rows×cols?
            if isinstance(g, list) and g and isinstance(g[0], list):
                return g

            # list of bit-mask columns, e.g., [0b010, 0b111, ...]
            if isinstance(g, list) and g and isinstance(g[0], int):
                height = max(1, max(c.bit_length() for c in g))
                out = []
                for r in range(height - 1, -1, -1):  # MSB = top row
                    out.append([(c >> r) & 1 for c in g])
                return out

            # list of '01010' strings
            if isinstance(g, list) and g and isinstance(g[0], str):
                return [[1 if ch == '1' else 0 for ch in row] for row in g]

            # model-like objects
            if hasattr(g, 'rows'):
                rows = getattr(g, 'rows')
                if isinstance(rows, list) and rows and isinstance(rows[0], list):
                    return rows
            if hasattr(g, 'grid'):
                grid = getattr(g, 'grid')
                if isinstance(grid, list) and grid and isinstance(grid[0], list):
                    return grid
            if hasattr(g, 'cols'):
                cols = getattr(g, 'cols')
                if isinstance(cols, list) and cols and isinstance(cols[0], int):
                    height = getattr(g, 'height', None)
                    if height is None:
                        height = max(1, max(c.bit_length() for c in cols))
                    out = []
                    for r in range(height - 1, -1, -1):
                        out.append([(c >> r) & 1 for c in cols])
                    return out

            # blank/none-like
            if g in (None, 0, []):
                return [[0]]

            raise TypeError(f'Unsupported glyph format: {type(g)!r}')

        def center_crop_rows(rows, target_h: int):
            h = len(rows)
            if h <= target_h:
                return rows
            trim = h - target_h
            top = trim // 2
            return rows[top:top + target_h]

        def downscale_rows_or_pool(rows, target_h: int):
            src_h = len(rows)
            if src_h <= target_h:
                return rows
            out = []
            for t in range(target_h):
                start = int(t * src_h / target_h)
                end = int((t + 1) * src_h / target_h)
                if end == start:
                    end = min(start + 1, src_h)
                width = len(rows[0])
                pooled = [0] * width
                for r in range(start, end):
                    src_row = rows[r]
                    for c in range(width):
                        pooled[c] = 1 if (pooled[c] or src_row[c]) else 0
                out.append(pooled)
            return out

        # --- assemble glyphs -----------------------------------------------------
        fit_mode = getattr(self.config, 'fit', 'error')
        glyphs = []
        for ch in self.config.text:
            ch = ch.upper()
            raw = source_map.get(ch)
            if raw is None:
                raise ValueError(f'Character {ch!r} not found in font_map')
            g = to_rows_cols(raw)
            if len(g) > MATRIX_HEIGHT:
                if fit_mode == 'crop':
                    g = center_crop_rows(g, MATRIX_HEIGHT)
                elif fit_mode == 'scale':
                    g = downscale_rows_or_pool(g, MATRIX_HEIGHT)
                else:
                    raise ValueError(f'Font height {len(g)} > display height {MATRIX_HEIGHT}')
            glyphs.append(g)

        frames: List[Frame] = []

        # --- horizontal scroll ---------------------------------------------------
        if self.config.direction == 'horizontal':
            glyph_ws = [len(g[0]) if g and g[0] else 0 for g in glyphs]
            total_w = sum(glyph_ws) + self.config.spacing * (len(glyph_ws) - 1 if glyph_ws else 0)

            # canvas is rows×total_w, height = MATRIX_HEIGHT
            canvas = [[0] * max(total_w, 1) for _ in range(MATRIX_HEIGHT)]
            x = 0
            for g, w in zip(glyphs, glyph_ws):
                h = len(g)
                vpad = max((MATRIX_HEIGHT - h) // 2, 0)
                for r in range(h):
                    if w:
                        canvas[vpad + r][x:x + w] = g[r]
                x += w + self.config.spacing

            offsets = range(0, total_w) if getattr(self.config, 'wrap', False) else range(-MATRIX_WIDTH, total_w)
            for off in offsets:
                window = [
                    [canvas[r][off + c] if 0 <= off + c < total_w else 0 for c in range(MATRIX_WIDTH)]
                    for r in range(MATRIX_HEIGHT)
                ]
                cols = [[window[r][c] for r in range(MATRIX_HEIGHT)] for c in range(MATRIX_WIDTH)]
                frames.append(Frame(grid=Grid(init_grid=cols)))

        # --- vertical scroll -----------------------------------------------------
        else:
            # Stack glyphs vertically with spacing, centered horizontally
            # 1) compute per-glyph sizes
            glyph_hs = [len(g) if g else 0 for g in glyphs]
            glyph_ws = [len(g[0]) if g and g[0] else 0 for g in glyphs]
            render_w = max([1] + glyph_ws)  # avoid 0-width canvas
            total_h = sum(glyph_hs) + self.config.spacing * (len(glyphs) - 1 if glyphs else 0)

            # 2) build a tall canvas (rows x cols)
            canvas = [[0] * render_w for _ in range(max(total_h, 1))]

            # 3) blit each glyph centered horizontally
            y = 0
            for g, gh, gw in zip(glyphs, glyph_hs, glyph_ws):
                x0 = (render_w - gw) // 2  # center horizontally
                for r in range(gh):
                    yy = y + r
                    if 0 <= yy < total_h and gw:
                        row = canvas[yy]
                        # OR the pixels in (no bounds issues because x0..x0+gw is inside render_w)
                        for c in range(gw):
                            if g[r][c]:
                                row[x0 + c] = 1
                y += gh + self.config.spacing

            # 4) slide a MATRIX_HEIGHT window up or down over the tall canvas
            if self.config.direction == 'vertical_up':
                # Start fully below the bottom and slide up into view
                offsets = range(total_h, -MATRIX_HEIGHT - 1, -1)
            else:  # 'vertical_down'
                # Start fully above the top and slide down into view
                offsets = range(-MATRIX_HEIGHT, total_h + 1)

            for off in offsets:
                # Extract a MATRIX_HEIGHT x render_w window at vertical offset 'off'
                window_rows = [
                    [canvas[off + r][c] if 0 <= off + r < total_h else 0 for c in range(render_w)]
                    for r in range(MATRIX_HEIGHT)
                ]
                cols = self._rows_to_cols(window_rows)
                frames.append(Frame(grid=Grid(init_grid=cols)))
        anim = Animation(frame_data=frames)
        anim.set_all_frame_durations(self.config.frame_duration)
        return anim

