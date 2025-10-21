from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Type, Optional


from typing import Optional, Type, List
from concurrent.futures import ThreadPoolExecutor
import inspect

def get_controllers(
    threaded: bool = False,
    max_workers: Optional[int] = None,
    controller_cls: Optional[Type] = None,
    devices: Optional[list] = None,
    **controller_kwargs
) -> List['LEDMatrixController']:
    """
    Create LEDMatrixController objects, optionally in parallel threads, and
    propagate the 'threaded' flag to the controller constructor when supported.
    """
    from is_matrix_forge.led_matrix.constants import DEVICES
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController

    _devices = devices or DEVICES
    _controller_cls = controller_cls or LEDMatrixController
    _max_workers = max_workers or len(_devices)

    # Introspect constructor to see which kwargs it accepts (so we don't
    # rely on brittle try/except around TypeErrors for unexpected kwargs).
    sig = inspect.signature(_controller_cls.__init__)
    accepted = set(sig.parameters.keys()) - {'self'}

    def create_controller(device):
        # Start with caller-provided kwargs
        kwargs = dict(controller_kwargs)
        kwargs['device'] = device

        # Only pass what the controller actually supports
        if 'default_brightness' in accepted and 'default_brightness' not in kwargs:
            kwargs['default_brightness'] = 100

        # Respect the factory's 'threaded' argument for the controller instance:
        # Prefer 'threaded', fall back to 'thread_safe', else omit.
        if 'threaded' in accepted:
            kwargs['threaded'] = threaded
        elif 'thread_safe' in accepted:
            kwargs['thread_safe'] = threaded

        return _controller_cls(**kwargs)

    # Factory threading (independent of controller threading)
    if not threaded or len(_devices) <= 1:
        return [create_controller(dev) for dev in _devices]

    with ThreadPoolExecutor(max_workers=_max_workers) as ex:
        return list(ex.map(create_controller, _devices))



def find_leftmost(controllers):
    """
    Return the physically leftmost controller on a Framework 16.

    Layout order:
        | L1 | L2 | [Keyboard] | R1 | R2 |

    Parameters:
        controllers (List[LEDMatrixController]):
            List of controller objects with a `.location` dict.

    Returns:
        Optional[LEDMatrixController]:
            The leftmost controller object, or None if list is empty.
    """
    if not controllers:
        return None

    def sort_key(ctrl):
        side = ctrl.location.get('side')
        slot = ctrl.location.get('slot', 0)
        # Map physical order: left side before right side
        side_order = 0 if side == 'left' else 1
        # On left: smaller slot = more left; on right: smaller slot = more left too
        return (side_order, slot)

    return min(controllers, key=sort_key)


def find_rightmost(controllers):
    """
    Return the physically rightmost controller on a Framework 16.

    Layout order:
        | L1 | L2 | [Keyboard] | R1 | R2 |

    Parameters:
        controllers (list):
            List of controller objects with a `.location` dict.

    Returns:
        LEDMatrixController | None:
            The rightmost controller object, or None if list is empty.
    """
    if not controllers:
        return None

    def sort_key(ctrl):
        side = ctrl.location.get('side')
        slot = ctrl.location.get('slot', 0)

        # Map physical order: left side before right side
        side_order = 0 if side == 'left' else 1

        # On left: larger slot = more right; on right: larger slot = more right
        return (side_order, slot)

    return max(controllers, key=sort_key)


