from enum import IntEnum
from is_matrix_forge.led_matrix.display.patterns.built_in.stencils import checkerboard, every_nth_col, every_nth_row, all_brightnesses
from is_matrix_forge.led_matrix.hardware import send_command
from is_matrix_forge.led_matrix.commands.map import CommandVals


PATTERN_MAP = {
    "All LEDs on": lambda dev: send_command(dev, CommandVals.Pattern, [PatternVals.FullBrightness]),
    "Gradient (0-13% Brightness)": lambda dev: send_command(dev, CommandVals.Pattern, [PatternVals.Gradient]),
    "Double Gradient (0-7-0% Brightness)": lambda dev: send_command(dev, CommandVals.Pattern, [PatternVals.DoubleGradient]),
    "\"LOTUS\" sideways": lambda dev: send_command(dev, CommandVals.Pattern, [PatternVals.DisplayLotus]),
    "Zigzag": lambda dev: send_command(dev, CommandVals.Pattern, [PatternVals.ZigZag]),
    "\"PANIC\"": lambda dev: send_command(dev, CommandVals.Pattern, [PatternVals.DisplayPanic]),
    "\"LOTUS\" Top Down": lambda dev: send_command(dev, CommandVals.Pattern, [PatternVals.DisplayLotus2]),
    "All brightness levels (1 LED each)": lambda dev: all_brightnesses(dev),
    "Every Second Row": lambda dev: every_nth_row(dev, 2),
    "Every Third Row": lambda dev: every_nth_row(dev, 3),
    "Every Fourth Row": lambda dev: every_nth_row(dev, 4),
    "Every Fifth Row": lambda dev: every_nth_row(dev, 5),
    "Every Sixth Row": lambda dev: every_nth_row(dev, 6),
    "Every Second Col": lambda dev: every_nth_col(dev, 2),
    "Every Third Col": lambda dev: every_nth_col(dev, 3),
    "Every Fourth Col": lambda dev: every_nth_col(dev, 4),
    "Every Fifth Col": lambda dev: every_nth_col(dev, 5),
    "Checkerboard": lambda dev: checkerboard(dev, 1),
    "Double Checkerboard": lambda dev: checkerboard(dev, 2),
    "Triple Checkerboard": lambda dev: checkerboard(dev, 3),
    "Quad Checkerboard": lambda dev: checkerboard(dev, 4),
}


class PatternVals(IntEnum):
    Percentage = 0x00
    Gradient = 0x01
    DoubleGradient = 0x02
    DisplayLotus = 0x03
    ZigZag = 0x04
    FullBrightness = 0x05
    DisplayPanic = 0x06
    DisplayLotus2 = 0x07

    @classmethod
    def as_dict(cls) -> dict[str, int]:
        """
        Returns a dictionary of {name: value} for all enum members.

        Returns
        -------
        dict[str, int]
            A dictionary mapping enum names to their integer values.
        """
        return {member.name: member.value for member in cls}

    @classmethod
    def names(cls) -> list[str]:
        return list(cls.as_dict().keys())

    @classmethod
    def values(cls) -> list[int]:
        return list(cls.as_dict().values())

    @classmethod
    def items(cls) -> list[tuple[str, int]]:
        return list(cls.as_dict().items())
