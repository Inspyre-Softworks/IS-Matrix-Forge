from collections.abc import Mapping
from dataclasses import dataclass
from typing import Dict, List, Callable

from is_matrix_forge.led_matrix.display.grid.base import MATRIX_WIDTH, MATRIX_HEIGHT
from is_matrix_forge.led_matrix.display.grid import Grid
from is_matrix_forge.led_matrix.display.animations.animation import Animation, Frame
from .text.glyph_normalizer import GlyphNormalizer, GlyphRows


@dataclass(frozen=True)
class TextScrollerConfig:
    """Configuration for :class:`TextScroller`.

    Attributes:
        text: The string to display.
        font_map: Mapping of characters to glyph definitions (row-major 0/1 lists).
        spacing: Number of blank columns/rows between glyphs.
        frame_duration: Seconds each frame is displayed.
        wrap: If ``True`` horizontal scroll loops seamlessly.
        direction: ``"horizontal"``, ``"vertical_up"``, or ``"vertical_down"``.
        fit: Behaviour when a glyph exceeds ``MATRIX_HEIGHT``. Valid values are
            ``"error"`` (raise), ``"truncate"`` (center crop), and ``"clip"``
            (downscale with pooling). Legacy values ``"crop"`` and ``"scale"``
            are also accepted for backward compatibility.
        case_sensitive: When ``False`` (default) characters are normalized to
            uppercase before lookup.
    """

    text: str
    font_map: Mapping[str, List[List[int]]]
    spacing: int = 1
    frame_duration: float = 0.05
    wrap: bool = False  # unused for vertical mode
    direction: str = "horizontal"  # one of: "horizontal", "vertical_up", "vertical_down"
    fit: str = "error"
    case_sensitive: bool = False


class TextScroller:
    """Generates scrolling-text Animations in horizontal or vertical directions."""

    VALID_DIRS = {"horizontal", "vertical_up", "vertical_down"}
    VALID_FIT_MODES = ("error", "truncate", "clip")

    def __init__(self, config: TextScrollerConfig):
        self.config = config
        if config.direction not in self.VALID_DIRS:
            raise ValueError(f'Unsupported scroll direction: {config.direction}')

        self._normalizer = GlyphNormalizer(MATRIX_WIDTH, MATRIX_HEIGHT)

        normalized_map: Dict[str, GlyphRows] = {}
        for key, glyph in dict(config.font_map).items():
            normal_key = key if config.case_sensitive else str(key).upper()
            normalized_map[normal_key] = self._normalizer.normalize(glyph)

        if not normalized_map:
            raise ValueError('font_map must contain at least one glyph definition')

        sample = next(iter(normalized_map.values()))
        if len(sample) > MATRIX_HEIGHT:
            raise ValueError(f'Font height {len(sample)} > display height {MATRIX_HEIGHT}')

        self._rows_map = normalized_map

    def generate_animation(self) -> Animation:
        '''
        Build and return the scrolling-text Animation.

        Raises:
            ValueError:
                If any character is missing from the font_map, or if a glyph exceeds
                MATRIX_HEIGHT and fit='error'.
        '''
        source_map = self._rows_map

        legacy_fit = {'crop': 'truncate', 'scale': 'clip'}
        fit_mode = legacy_fit.get(self.config.fit, self.config.fit)
        if fit_mode not in self.VALID_FIT_MODES:
            valid_str = ', '.join(self.VALID_FIT_MODES)
            raise ValueError(f"Invalid fit mode '{self.config.fit}'. Valid options are: {valid_str}")

        transform: Callable[[str], str]
        transform = (lambda c: c) if self.config.case_sensitive else str.upper

        def center_crop_rows(rows: GlyphRows, target_h: int) -> GlyphRows:
            if len(rows) <= target_h:
                return [r[:] for r in rows]
            trim = len(rows) - target_h
            top = trim // 2
            return [row[:] for row in rows[top:top + target_h]]

        def downscale_rows_or_pool(rows: GlyphRows, target_h: int) -> GlyphRows:
            src_h = len(rows)
            if src_h <= target_h:
                return [r[:] for r in rows]
            out: GlyphRows = []
            width = len(rows[0]) if rows and rows[0] else 0
            for t in range(target_h):
                start = int(t * src_h / target_h)
                end = int((t + 1) * src_h / target_h)
                if end == start:
                    end = min(start + 1, src_h)
                pooled = [0] * width
                for r in range(start, end):
                    src_row = rows[r]
                    for c in range(width):
                        pooled[c] = 1 if (pooled[c] or src_row[c]) else 0
                out.append(pooled)
            return out

        glyphs: List[GlyphRows] = []
        for ch in self.config.text:
            lookup = transform(ch)
            raw = source_map.get(lookup)
            if raw is None:
                raise ValueError(f'Character {ch!r} not found in font_map')
            glyph_rows = [row[:] for row in raw]
            if len(glyph_rows) > MATRIX_HEIGHT:
                if fit_mode == 'truncate':
                    glyph_rows = center_crop_rows(glyph_rows, MATRIX_HEIGHT)
                elif fit_mode == 'clip':
                    glyph_rows = downscale_rows_or_pool(glyph_rows, MATRIX_HEIGHT)
                else:
                    raise ValueError(f'Font height {len(glyph_rows)} > display height {MATRIX_HEIGHT}')
            glyphs.append(glyph_rows)

        frames: List[Frame] = []

        if not glyphs:
            if self.config.text:
                raise ValueError('No glyphs could be generated for the configured text')
            blank = Grid()
            frames.append(Frame(grid=blank))
            anim = Animation(frame_data=frames)
            anim.set_all_frame_durations(self.config.frame_duration)
            return anim

        # --- horizontal scroll ---------------------------------------------------
        if self.config.direction == 'horizontal':
            glyph_ws = [len(g[0]) if g and g[0] else 0 for g in glyphs]
            total_w = sum(glyph_ws) + self.config.spacing * (len(glyph_ws) - 1 if glyph_ws else 0)

            # canvas is rows×total_w, height = MATRIX_HEIGHT
            if total_w == 0:
                frames.append(Frame())
                anim = Animation(frame_data=frames)
                anim.set_all_frame_durations(self.config.frame_duration)
                return anim

            canvas = [[0] * max(total_w, 1) for _ in range(MATRIX_HEIGHT)]
            x = 0
            for g, w in zip(glyphs, glyph_ws):
                h = len(g)
                vpad = max((MATRIX_HEIGHT - h) // 2, 0)
                for r in range(h):
                    if w:
                        canvas[vpad + r][x:x + w] = g[r]
                x += w + self.config.spacing

            offsets = range(total_w) if getattr(self.config, 'wrap', False) else range(-MATRIX_WIDTH, total_w)
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
            if all(w == 0 for w in glyph_ws):
                blank_grid = Grid()
                frames.append(Frame(grid=blank_grid))
                anim = Animation(frame_data=frames)
                anim.set_all_frame_durations(self.config.frame_duration)
                return anim
            render_w = max(glyph_ws)
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
                cols = self._normalizer.rows_to_cols(window_rows)
                frames.append(Frame(grid=Grid(init_grid=cols)))
        anim = Animation(frame_data=frames)
        anim.set_all_frame_durations(self.config.frame_duration)
        return anim

