from is_matrix_forge.led_matrix.errors.base import LEDMatrixControllerError


class SceneError(LEDMatrixControllerError):
    """
    Base class for all scene related errors.
    """
    default_message = "An error occurred while processing the scene."


class SceneNotBuiltError(SceneError):
    default_message = "The scene has not been built yet. Try calling `build()` first."
