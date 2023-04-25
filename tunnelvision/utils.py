import asyncio

from tunnelvision.logger import logger

__all__ = [
    "Singleton",
    "is_ipython_session",
    "handle_task_exception",
]


# `True` if the user is running code in an iPython session.
# This is required to be able to use the viewer.
_IS_IPYTHON_SESSION = None


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def is_ipython_session() -> bool:
    """Returns if the python is an iPython session.

    Adapted from
    https://discourse.jupyter.org/t/find-out-if-my-code-runs-inside-a-notebook-or-jupyter-lab/6935/3
    """
    global _IS_IPYTHON_SESSION
    if _IS_IPYTHON_SESSION is not None:
        return _IS_IPYTHON_SESSION

    is_ipython_session = None
    try:
        from IPython import get_ipython

        ip = get_ipython()
        is_ipython_session = ip is not None
    except ImportError:
        # iPython is not installed
        is_ipython_session = False
    _IS_IPYTHON_SESSION = is_ipython_session
    return _IS_IPYTHON_SESSION


def handle_task_exception(task: "asyncio.Task"):
    """Handle exceptions in tasks."""

    if task.exception() is not None:
        logger.error(f"Task `{task}` raised an exception: {task.exception()}")
