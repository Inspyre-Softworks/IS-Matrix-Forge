try:  # pragma: no cover - fallback when inspy_logger is unavailable
    from inspy_logger import InspyLogger, Loggable
    from inspy_logger.constants import LEVEL_MAP

    LOG_LEVELS = [level for level in LEVEL_MAP.keys()]
    del LEVEL_MAP

    PROGNAME = 'IS-Matrix-Forge'
    AUTHOR = 'Inspyre-Softworks'

    INSPY_LOG_LEVEL = 'INFO'
    ROOT_LOGGER = InspyLogger(PROGNAME, console_level='info', no_file_logging=True)
except ModuleNotFoundError:  # pragma: no cover - simplified logging
    import logging

    class Loggable:  # minimal stub
        def __init__(self, logger=None, parent_log_device=None, **kwargs):
            chosen = logger or parent_log_device
            self.class_logger = chosen or logging.getLogger(__name__)
            self.method_logger = self.class_logger

    LOG_LEVELS = list(logging._nameToLevel.keys())
    PROGNAME = 'IS-Matrix-Forge'
    AUTHOR = 'Inspyre-Softworks'
    INSPY_LOG_LEVEL = 'INFO'
    class _Logger(logging.Logger):
        def get_child(self, name):
            return self.getChild(name)

    logging.setLoggerClass(_Logger)
    ROOT_LOGGER = logging.getLogger(PROGNAME)
    ROOT_LOGGER.setLevel(logging.INFO)



def _norm_level(level) -> int:
    import logging

    if isinstance(level, int):
        return level
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.DEBUG)
    return logging.DEBUG


def log_on_exception(
    *,
    level='debug',
    reraise: bool = False,
    logger_attr: str = 'LOGGER',
    fallback_logger=None,
    msg=None,
):
    """
    Decorator: log exceptions at `level` with exc_info=True, optionally re-raise.

    - If bound method, uses `self.LOGGER` or `cls.LOGGER` (name configurable via `logger_attr`).
    - Otherwise uses `fallback_logger` (defaults to a child of ROOT_LOGGER).
    """
    import logging
    from functools import wraps

    lvl = _norm_level(level)

    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:  # intentionally broad: we're *logging* and (optionally) swallowing
                bound_logger = fallback_logger or ROOT_LOGGER.get_child('log_on_exception')
                if args:
                    candidate = getattr(args[0], logger_attr, None)
                    if isinstance(candidate, logging.Logger):
                        bound_logger = candidate

                text = msg or f'Exception in {fn.__qualname__}: {e!r}'
                bound_logger.log(lvl, text, exc_info=True)
                if reraise:
                    raise
        return wrapper
    return deco


__all__ = [
    'AUTHOR',
    'INSPY_LOG_LEVEL',
    'Loggable',
    'LOG_LEVELS',
    'PROGNAME',
    'ROOT_LOGGER',
    'log_on_exception',
]

