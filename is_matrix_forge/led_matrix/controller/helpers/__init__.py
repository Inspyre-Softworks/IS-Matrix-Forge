from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Type, Optional


def get_controllers(
    threaded: bool = False,
    max_workers: Optional[int] = None,
    controller_cls: Optional[Type] = None,
    devices: Optional[list] = None,
    **controller_kwargs
) -> List['LEDMatrixController']:
    """
    Create LEDMatrixController objects, optionally in parallel threads.

    Parameters:
        threaded (bool): If True, create controllers in threads.
        max_workers (int, optional): Maximum threads to use (default: len(devices)).
        controller_cls (Type, optional): Alternate controller class (default: LEDMatrixController).
        devices (list, optional): Device list (default: imported DEVICES).
        **controller_kwargs: Additional kwargs for controller class.

    Returns:
        List[LEDMatrixController]: List of controller instances.
    """
    from is_matrix_forge.led_matrix.constants import DEVICES
    from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController

    _devices = devices or DEVICES
    _controller_cls = controller_cls or LEDMatrixController
    _max_workers = max_workers or len(_devices)

    def create_controller(device):
        # Here’s where you could add try/except if your hardware is flaky!
        return _controller_cls(device=device, default_brightness=100, thread_safe=True, **controller_kwargs)

    if not threaded:
        return [create_controller(dev) for dev in _devices]

    with ThreadPoolExecutor(max_workers=_max_workers) as executor:
        futures = [executor.submit(create_controller, dev) for dev in _devices]
        controllers = []
        for fut in as_completed(futures):
            controllers.append(fut.result())
        return controllers
