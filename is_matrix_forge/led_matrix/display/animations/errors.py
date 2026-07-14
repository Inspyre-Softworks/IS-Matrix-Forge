from is_matrix_forge.led_matrix.errors.base import LEDMatrixControllerError
from is_matrix_forge.led_matrix.errors.grid import GridDefinitionError, MalformedGridError


class AnimationFinishedError(LEDMatrixControllerError, RuntimeError):
    default_message = 'Animation has finished!'

    def __init__(self, message: str = None, **kwargs) -> None:
        if message is not None:
            self.default_message = f"{self.default_message}\n\n  Additional information from caller:\n    {message}"

        super().__init__(message=self.default_message, **kwargs)


__all__ = ['AnimationFinishedError', 'GridDefinitionError', 'MalformedGridError']

