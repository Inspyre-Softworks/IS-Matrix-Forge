try:  # pragma: no cover - fallback when inspy_logger is unavailable
    from inspy_logger import InspyLogger, Loggable
    from inspy_logger.constants import LEVEL_MAP

    LOG_LEVELS = [level for level in LEVEL_MAP.keys()]
    del LEVEL_MAP

    PROGNAME = 'LEDMatrixBattery'
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
    PROGNAME = 'LEDMatrixBattery'
    AUTHOR = 'Inspyre-Softworks'
    INSPY_LOG_LEVEL = 'INFO'
    class _Logger(logging.Logger):
        def get_child(self, name):
            return self.getChild(name)

    logging.setLoggerClass(_Logger)
    ROOT_LOGGER = logging.getLogger(PROGNAME)
    ROOT_LOGGER.setLevel(logging.INFO)



__all__ = [
    'AUTHOR',
    'INSPY_LOG_LEVEL',
    'Loggable',
    'LOG_LEVELS',
    'PROGNAME',
    'ROOT_LOGGER',
]

