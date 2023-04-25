import logging
import os

__all__ = ["get_logger", "logger"]


def get_logger(name: str):
    """Get a logger for the given name.

    Args:
        name (str): The name of the logger.

    Returns:
        logging.Logger: The logger.
    """
    logger = logging.getLogger(name)
    level = os.environ.get("TUNNELVISION_LOG_LEVEL", logging.WARNING)
    logger.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


logger = get_logger("tunnelvision")
