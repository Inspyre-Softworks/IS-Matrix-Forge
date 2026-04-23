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
