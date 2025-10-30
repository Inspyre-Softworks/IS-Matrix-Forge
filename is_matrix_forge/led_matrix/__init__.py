"""
LED Matrix package initialization.

Keep this module light: no hardware access, no file IO, no heavy imports.
"""

from __future__ import annotations

from .utils import (
    get_first_run,
    set_first_run,
    process_first_run,
    initialize,
)

__all__ = [
    'get_first_run',
    'set_first_run',
    'process_first_run',
    'initialize',
    'LEDMatrixController',
    'get_controllers',
    'scroll_text_on_multiple_matrices',
]


def __getattr__(name: str):
    if name in ('LEDMatrixController', 'get_controllers'):
        from .controller import LEDMatrixController, get_controllers
        globals().update({
            'LEDMatrixController': LEDMatrixController,
            'get_controllers': get_controllers,
        })
        return globals()[name]

    if name == 'scroll_text_on_multiple_matrices':
        from .display.text.scroller import scroll_text_on_multiple_matrices
        globals()['scroll_text_on_multiple_matrices'] = scroll_text_on_multiple_matrices
        return scroll_text_on_multiple_matrices

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
