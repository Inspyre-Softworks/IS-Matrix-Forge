import difflib
from typing import Any

from is_matrix_forge.led_matrix.display.patterns.built_in.stencils.res import PATTERN_MAP


class BuiltInPatterns:
    """
    Interface for rendering built-in LED matrix patterns on a device.

    Parameters
    ----------
    dev : Any
        The device instance to send commands to.
    """

    def __init__(self, dev: Any):
        from serial.tools.list_ports_common import ListPortInfo
        from is_matrix_forge.led_matrix.controller.controller import LEDMatrixController

        if dev is None:
            from is_matrix_forge.led_matrix.controller.helpers import get_controllers

        if not isinstance(dev, ListPortInfo) and not isinstance(dev, LEDMatrixController):
            raise TypeError(f'dev must be of type `ListPortInfo` or `LEDMatrixController`, not {type(dev)}')
        elif isinstance(dev, LEDMatrixController):
            dev = dev.device

        self.dev = dev

    def render(self, pattern_name: str) -> None:
        """
        Render the specified pattern on the device.

        Parameters
        ----------
        pattern_name : str
            The name of the pattern to render.
        """
        normalized = self._normalize(pattern_name)
        action = PATTERN_MAP.get(normalized)

        if action:
            action(self.dev)
        else:
            print(f"❌ Invalid pattern: '{pattern_name}'")
            suggestions = self.suggest(pattern_name)
            if suggestions:
                print("💡 Did you mean:")
                for s in suggestions:
                    print(f"  - {s}")
            else:
                print("ℹ️ Available patterns:")
                for key in self.list():
                    print(f"  - {key}")

    def suggest(self, pattern_name: str, n: int = 3) -> list[str]:
        """
        Suggest similar pattern names.

        Parameters
        ----------
        pattern_name : str
            The name to suggest alternatives for.

        n : int, optional
            Maximum number of suggestions to return.

        Returns
        -------
        list[str]
            List of suggested pattern names.
        """
        return difflib.get_close_matches(pattern_name, self.list(), n=n)

    @staticmethod
    def list() -> list[str]:
        """
        List all available pattern names.

        Returns
        -------
        list[str]
            Names of all patterns available.
        """
        return list(PATTERN_MAP.keys())

    @staticmethod
    def _normalize(name: str) -> str:
        return name.strip()

