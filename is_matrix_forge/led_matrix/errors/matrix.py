try:
    from inspyre_toolbox.exceptional import CustomRootException
except ModuleNotFoundError:  # pragma: no cover - fallback
    class CustomRootException(Exception):
        pass
from .base import LEDMatrixControllerError


class MatrixError(LEDMatrixControllerError):
    """
    Base class for all LED matrix errors.

    Subclasses of this exception are used to indicate specific errors that can occur while interacting with the LED
    matrix hardware.

    Provided Subclasses:
        - MatrixConnectionError:
            Raised when the LED matrix cannot be connected to.

        - MatrixInUseError:
            Raised when the LED matrix is already in use by another process.
    """
    default_message = 'An error occurred while interacting with the LED matrix!'

    def __init__(self, message: str = None, device_name: str = None) -> None:
        full_msg = self.default_message

        if device_name is not None:
            full_msg += f' (Device: {device_name})'

        if message is not None:
            full_msg = f'{full_msg}\n\n  Additional Info:\n{" " * 4}{message}'

        super().__init__(full_msg)


class MatrixConnectionError(MatrixError):
    """
    Raised when the LED matrix cannot be connected to.
    """
    default_message = 'Unable to connect to the LED matrix!'

    def __init__(self, message: str = None) -> None:
        if message is None:
            message = self.default_message
        else:
            message = f'{self.default_message}\n\n  Additional Info:\n{" " * 4}{message}'

        super().__init__(message)


class MatrixInUseError(MatrixConnectionError):
    """
    Raised when the LED matrix is already in use by another process.
    """
    message = 'The LED matrix is already in use, and cannot be used by this program! Please close the other ' \
                      'instance/process and try again!'

    def __init__(self):
        super().__init__(self.message)


class InvalidBrightnessError(MatrixError):
    """
    Raised when the brightness value provided is invalid.
    """
    default_message = 'The brightness value provided is invalid! Value must be an integer between 0 and 255!'

    def __init__(self, brightness: int):
        message = f'{self.default_message}\n\n  Brightness: {brightness}'

        super().__init__(message)
