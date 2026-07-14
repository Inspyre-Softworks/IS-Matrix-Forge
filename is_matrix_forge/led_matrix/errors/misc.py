from .base import LEDMatrixControllerError


class MiscError(LEDMatrixControllerError):
    pass


class ImplicitNameDerivationError(MiscError, ValueError):
    """
    Raised by `freeze_setter` when it's used to decorate a property setter
    whose name begins with a single underscore (e.g., `_my_prop`) without an
    explicit `attr_name` being provided.

    This error occurs because the default behavior of `freeze_setter` is to
    derive the underlying private attribute name by prepending an underscore
    to the setter's name. If the setter is `_my_prop`, this would implicitly
    attempt to create `__my_prop`. Attributes starting with double underscores
    trigger Python's name mangling, which can lead to unexpected behavior and
    make the underlying attribute name less predictable if not explicitly intended.

    To prevent this implicit and potentially confusing name derivation,
    `freeze_setter` requires that you explicitly specify the `attr_name`
    when decorating setters that start with a single underscore.

    TL;DR: When using `freeze_setter` on a property setter named `_my_prop`,
    you must explicitly specify the `attr_name` as "__my_prop" to avoid confusion
    about how the underlying attribute will be named, and to confirm your intent.
    """
    default_message = (
        "Implicitly derived attribute names are not allowed for properties "
        "whose names begin with a single underscore. Please provide an "
        "`attr_name` argument."
    )

    def __init__(self, **kwargs):
        super().__init__(message=self.default_message, **kwargs)
