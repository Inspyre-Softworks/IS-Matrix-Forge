from inspyre_toolbox.exceptional import CustomRootException


class LEDMatrixControllerError(CustomRootException):
    """
    Base exception for LEDMatrixController errors.
    """
    pass


class LEDMatrixControllerPropReadError(LEDMatrixControllerError):
    """
    Exception raised when a property is read from a LEDMatrixController instance.
    """
    default_message = 'Failed to read property from LEDMatrixController instance'

    def __init__(self, *args, property_name: str = None, reason: str = None ):
        self.property_name = property_name
        self.reason = reason
        super().__init__(f'{self.default_message}: {property_name or "Not specified"} - {reason or "No reason provided"}', *args)


class LEDMatrixControllerPropWriteError(LEDMatrixControllerError):
    """
    Exception raised when a property is written to a LEDMatrixController instance.
    """
    default_message = 'Failed to write property to LEDMatrixController instance'

    def __init__(self, *args, property_name: str = None, reason: str = None ):
        self.property_name = property_name
        self.reason = reason
        super().__init__(f'{self.default_message}: {property_name or "Not specified"} - {reason or "No reason provided"}', *args)


class LEDMatrixControllerGameError(LEDMatrixControllerError):
    """
    Base exception for controller game-mode errors.
    """


class LEDMatrixControllerGameRunningError(LEDMatrixControllerGameError):
    """
    Raised when a normal controller operation is attempted while a game is active.
    """

    default_message = 'Cannot perform this controller operation while a device game is running'

    def __init__(self, *args, method_name: str = None, game = None):
        self.method_name = method_name
        self.game = game
        game_name = getattr(game, 'name', game) if game is not None else 'Unknown'
        super().__init__(
            f'{self.default_message}: {method_name or "Unknown method"} - active game: {game_name}',
            *args,
        )


class LEDMatrixControllerGameNotRunningError(LEDMatrixControllerGameError):
    """
    Raised when a game control is sent but no tracked game is active.
    """

    default_message = 'Cannot send a game control because no device game is currently running'

    def __init__(self, *args, control = None):
        self.control = control
        control_name = getattr(control, 'name', control) if control is not None else 'Unknown'
        super().__init__(f'{self.default_message}: {control_name}', *args)
