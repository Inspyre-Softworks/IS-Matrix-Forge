from inspyre_toolbox.exceptional import CustomRootException


class GridDefinitionError(CustomRootException, ValueError):
    default_message = 'An error has occurred within the grid definition!'


class MalformedGridError(GridDefinitionError):
    """
    Raised when the grid is malformed.

    Class Attributes:
        default_message (str):
            **Read-Only**. The default message for the error.
    """
    default_message = 'The grid is malformed!'

    def __init__(self, more_info: str = None, **kwargs) -> None:
        if more_info is not None:
            self.default_message = f"{self.default_message}\n\n  Additional information from caller:\n    {more_info}"

        super().__init__(message=self.default_message, **kwargs)


class AnimationFinishedError(CustomRootException, RuntimeError):
    default_message = 'Animation has finished!'

    def __init__(self, message: str = None, **kwargs) -> None:
        if message is not None:
            self.default_message = f"{self.default_message}\n\n  Additional information from caller:\n    {message}"

        super().__init__(message=self.default_message, **kwargs)

