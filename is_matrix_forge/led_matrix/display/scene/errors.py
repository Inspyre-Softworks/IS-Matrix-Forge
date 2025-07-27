from inspyre_toolbox.exceptional import CustomRootException


class SceneError(CustomRootException):
    """
    Base class for all scene related errors.
    """
    default_message = "An error occurred while processing the scene."


class SceneNotBuiltError(SceneError):
    default_message = "The scene has not been built yet. Try calling `build()` first."
