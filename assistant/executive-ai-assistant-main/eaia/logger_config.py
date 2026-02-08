import logging
import os


def setup_logging(name: str = "eaia") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    level = os.getenv("EAIA_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level, logging.INFO))
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger



