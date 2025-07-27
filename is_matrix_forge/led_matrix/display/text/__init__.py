from .scroller import TextScroller
"""
Text and symbol rendering module for LED Matrix.

This module provides functions for displaying text and symbols on the LED matrix.
It includes functions for rendering strings, fonts, and special symbols.
"""

from ..assets import fonts as font
from ...hardware import send_command
from ...commands.map import CommandVals


def show_string(dev, s):
    """Render a string with up to five letters"""
    show_font(dev, [font.convert_font(letter) for letter in str(s)[:5]])


def show_font(dev, font_items):
    """Render up to five 5x6 pixel font items"""
    # Initialize a byte array with all pixels off
    vals = [0x00 for _ in range(39)]

    # Process each font item (character/symbol)
    for digit_i, digit_pixels in enumerate(font_items):
        # Calculate vertical offset for this character
        # Each character is placed 7 pixels apart vertically
        offset = digit_i * 7

        # Process each pixel in the 5x6 character grid
        for pixel_x in range(5):
            for pixel_y in range(6):
                # Convert 2D coordinates to 1D index in the font data
                # Font data is stored as a 1D array in row-major order
                pixel_value = digit_pixels[pixel_x + pixel_y * 5]

                # Calculate the position in the LED matrix
                # Characters start at x=2 (to center them) and are stacked vertically
                # with the calculated offset
                i = (2 + pixel_x) + (9 * (pixel_y + offset))

                # If this pixel should be on
                if pixel_value:
                    # Calculate which byte and bit to set
                    byte_index = int(i / 8)
                    bit_position = i % 8

                    # Set the bit in the appropriate byte
                    vals[byte_index] = vals[byte_index] | (1 << bit_position)

    # Send the command to display the characters
    send_command(dev, CommandVals.Draw, vals)


def show_symbols(dev, symbols):
    """Render a list of up to five symbols
    Can use letters/numbers or symbol names, like 'sun', ':)'"""
    font_items = []
    for symbol in symbols:
        s = font.convert_symbol(symbol)
        if not s:
            s = font.convert_font(symbol)
        font_items.append(s)

    show_font(dev, font_items)

