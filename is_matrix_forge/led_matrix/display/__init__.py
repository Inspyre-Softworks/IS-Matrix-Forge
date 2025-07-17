"""
Display module for LED Matrix.

This module provides functions for displaying various content on the LED matrix,
including patterns, text, and media.
"""

# Import and re-export all display-related functions
from .patterns.built_in.stencils import checkerboard
from .helpers import light_leds
from .helpers.columns import send_col
from .text import show_string, show_font, show_symbols
from .media import image, image_greyscale, camera, video, pixel_to_brightness
