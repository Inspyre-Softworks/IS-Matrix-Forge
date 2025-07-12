import functools
from typing import Optional, Type, Callable, Any


def freeze_setter(
    attr_name: Optional[str] = None,
    exception: Type[Exception] = AttributeError,
    allow_none_reassignment: bool = False,
    treat_none_as_unset: bool = True,
    allow_reassignment_to_same_value: bool = False,
    fail_silently: bool = False
):
    """
    Function decorator for a @<prop>.setter that raises if you try to set again.

    This decorator prevents reassigning a property after it's been set once,
    with configurable exceptions.

    Parameters:
        attr_name (str, optional):
            The name of the underlying private attribute to check. If not provided,
            it will be derived from the setter's function name by prepending a
            single underscore (e.g., `value` becomes `_value`). If your setter
            name starts with a single underscore (e.g., `_internal_val`), you *must*
            provide this parameter explicitly.
        exception (Exception class, optional):
            The exception to raise on reassignment.
            Defaults to raise an AttributeError.
        allow_none_reassignment (bool, optional):
            If True, allows setting the property to None even if it's already set.
            Defaults to False.
        treat_none_as_unset (bool, optional):
            If True, None values are considered as unset, allowing the property
            to be set if its current value is None.
            Defaults to True.
        allow_reassignment_to_same_value (bool, optional):
            If True, allows reassigning the property with the same value.
            It passes silently and does not call the setter again.
            Defaults to False.
        fail_silently (bool, optional):
            If True, instead of raising an exception on a forbidden reassignment,
            the setter simply returns silently.
            Defaults to False.

    Raises:
        ImplicitNameDerivationError:
            If the decorated setter's name starts with a single underscore
            (but not a double underscore, which has its own meaning) and
            `attr_name` is not provided. This is to prevent accidental
            triggering of Python's name mangling.
        exception: (Defaults to AttributeError)
            Raised when a forbidden attempt to reassign the property occurs,
            unless `fail_silently` is True.

    Example:
        ```python
        class MyClass:
            def __init__(self):
                self._value = None # Underlying attribute

            @property
            def value(self):
                return self._value

            @value.setter
            @freeze_setter() # Derives attr_name as '_value'
            def value(self, new_value):
                self._value = new_value

        obj = MyClass()
        obj.value = 42
        # obj.value = 100  # Raises AttributeError

        class InternalPropClass:
            def __init__(self):
                self.__internal_storage = None # Explicit private attribute

            @property
            def _internal_prop(self):
                return self.__internal_storage

            @_internal_prop.setter
            @freeze_setter(attr_name='__internal_storage') # Must provide attr_name
            def _internal_prop(self, new_value):
                self.__internal_storage = new_value
        ```

    See Also:
        - `ImplicitNameDerivationError`: Raised for configuration issues with underscore-prefixed setters.
        - `AttributeError`: Default exception for reassigning a frozen attribute.
    """
    from is_matrix_forge.led_matrix.errors.misc import ImplicitNameDerivationError

    def decorator(setter: Callable) -> Callable:
        setter_name = setter.__name__

        # Check if the setter name starts with a single '_' and attr_name isn't provided.
        # We allow double underscores ('__') as they have special meaning and are less likely
        # to be used for regular property setters that would rely on implicit derivation.
        if setter_name.startswith('_') and not setter_name.startswith('__') and attr_name is None:
            raise ImplicitNameDerivationError()  # Raise error if no explicit attr_name is given for such setters.

        private_attr_name = attr_name or f'_{setter_name}'

        @functools.wraps(setter)
        def wrapper(self, new_value: Any) -> Any:
            current_value = getattr(self, private_attr_name, None)

            # Determine if the attribute is considered 'set'
            # An attribute is considered "set" if:
            # 1. treat_none_as_unset is False (meaning None is a valid set value)
            # OR
            # 2. treat_none_as_unset is True AND current_value is not None
            is_set = not treat_none_as_unset or current_value is not None

            if is_set:
                # Case 1: Reassigning to the same value is allowed and current value matches new value
                if allow_reassignment_to_same_value and new_value == current_value:
                    return  # Pass silently without calling setter or raising

                # Case 2: Reassigning to None is allowed and new value is None
                # This only applies if the property is already considered "set".
                # If treat_none_as_unset is True, setting to None effectively "unsets" it.
                if allow_none_reassignment and new_value is None:
                    return setter(self, new_value)  # Allow and call setter

                # Case 3: Forbidden reassignment
                if fail_silently:
                    return  # Fail silently

                raise exception(
                    f"Cannot reassign {self.__class__.__name__}.{setter_name} "
                    f"(current value: {current_value!r}, private attribute: '{private_attr_name}')"
                )

            # If the attribute wasn't considered set, or if it's being set to None
            # when treat_none_as_unset is True (which is like an initial set), call the setter.
            return setter(self, new_value)

        return wrapper

    return decorator
