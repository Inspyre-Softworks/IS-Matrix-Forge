try:
    from inspyre_toolbox.exceptional import CustomRootException
except ModuleNotFoundError:  # pragma: no cover - fallback
    class CustomRootException(Exception):
        pass


class LEDMatrixControllerError(CustomRootException):
    """
    Base class for all LED matrix controller errors.

    Class Attributes:
        default_message (str): Read-Only. The default message for the error.
    """
    default_message = 'An error occurred with the LED matrix controller library!'


__all__ = ['LEDMatrixControllerError']
