from typing import Any, Dict

class MultitonMeta(type):
    """
    Metaclass that ensures only one instance per “key” exists.
    By default, it uses the first positional argument (your `device`)
    and looks up its `.device` attribute (if present) or `repr()` as the unique key.
    """
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        # per–subclass registry
        cls._instances: Dict[Any, cls] = {}
        # allow subclasses to override which attr to use on device
        cls.MULTITON_KEY_ATTR: str = attrs.get('MULTITON_KEY_ATTR', 'device')

    def __call__(cls, *args, **kwargs):
        # pull out the “device” argument
        if cls.MULTITON_KEY_ATTR in kwargs:
            dev = kwargs[cls.MULTITON_KEY_ATTR]
        elif args:
            dev = args[0]
        else:
            raise TypeError(f"Missing '{cls.MULTITON_KEY_ATTR}' argument")
        # pick a raw key from either dev.<attr> or repr(dev)
        raw_key = getattr(dev, cls.MULTITON_KEY_ATTR, repr(dev))
        # return existing if we've already built one
        if raw_key in cls._instances:
            return cls._instances[raw_key]
        # otherwise build & cache a new one
        inst = super().__call__(*args, **kwargs)
        cls._instances[raw_key] = inst
        return inst
