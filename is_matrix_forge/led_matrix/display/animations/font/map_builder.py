# font_map_builder.py

"""
Author: Taylor
Project: Inspyre-Toolbox (LED-Matrix Extensions)
File: font_map_builder.py

Description:
    Build a mapping from characters to 2D binary grids
    suitable for driving your TextScroller.

Dependencies:
    - pillow (PIL)

Classes:
    FontMapBuilderConfig
    FontMapBuilder

Example Usage:
    from font_map_builder import FontMapBuilder, FontMapBuilderConfig

    config = FontMapBuilderConfig(
        font_path="C:/Windows/Fonts/arial.ttf",
        font_size=8,
        canvas_size=(5, 7),  # width x height in pixels
        characters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?,.",
        threshold=128,
    )
    builder  = FontMapBuilder(config)
    font_map = builder.generate_font_map()
    # font_map["A"] is now a 7-row x 5-col list of 0/1s
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class FontMapBuilderConfig:
    """Immutable settings for font‐to‐grid conversion."""
    font_path: str
    font_size: int
    canvas_size: Tuple[int, int]
    characters: str
    threshold: int = 128  # pixel brightness cutoff (0–255)


class FontMapBuilder:
    """Generates a font_map mapping each character to a binary grid."""

    def __init__(self, config: FontMapBuilderConfig):
        """
        Args:
            config: All settings needed to render and threshold glyphs.
        """
        self.config = config
        self._font = ImageFont.truetype(config.font_path, config.font_size)

    def generate_font_map(self) -> Dict[str, List[List[int]]]:
        """
        Render every character in `config.characters` into a
        monochrome grid, then threshold to 0/1.

        Returns:
            A dict mapping each character to its grid (rows of ints).
        """
        font_map: Dict[str, List[List[int]]] = {}
        w, h = self.config.canvas_size

        for char in self.config.characters:
            if char in self.config.characters:
                if char == ' ':
                    grid = [[0] * w for _ in range(h)]
                else:
                    img = self._render_char(char, w, h)
                    grid = self._image_to_grid(img)
                font_map[char] = grid

        if ' ' not in font_map:
            font_map[' '] = [[0] * w for _ in range(h)]

        return font_map

    def _render_char(self, ch: str, width: int, height: int) -> Image.Image:
        """
        Draw a single character centered in a WxH grayscale image.

        Returns:
            A Pillow Image in mode 'L'.
        """
        img = Image.new("L", (width, height), color=0)
        draw = ImageDraw.Draw(img)

        try:
            left, top, right, bottom = draw.textbbox((0, 0), ch, font=self._font)
            text_w, text_h = right - left, bottom - top
            x  = (width - text_w) // 2 - left
            y = (height - text_h) // 2 - top
        except AttributeError:
            # Maintain compatibility with pre 8.0.0 Pillow
            text_w, text_h = self._font.getsize(ch)
            x = (width - text_w) // 2
            y = (height - text_h) // 2

        draw.text((x, y), ch, fill=255, font=self._font)
        return img

    def _image_to_grid(self, img: Image.Image) -> List[List[int]]:
        """
        Convert a grayscale image to a 2D list of 0/1
        based on the luminosity threshold.

        Returns:
            List of rows, each a list of ints (0 or 1).
        """
        pixels = img.load()
        w, h = img.size
        thresh = self.config.threshold
        return [
            [1 if pixels[x, y] >= thresh else 0 for x in range(w)]
            for y in range(h)
        ]
