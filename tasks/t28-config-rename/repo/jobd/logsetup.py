"""Logging set up from settings."""
import logging

_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}


def configure(settings):
    logger = logging.getLogger("jobd")
    logger.setLevel(_LEVELS[settings.log_level])
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [" + settings.pool_name + "] %(message)s"))
        logger.addHandler(handler)
    return logger
