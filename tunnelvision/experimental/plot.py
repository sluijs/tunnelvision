import os
import socket
import subprocess
from typing import Tuple

import numpy as np
from IPython.display import IFrame, display

# Name of the localhost.
LOCALHOST_NAME = os.getenv("TUNNELVISION_HOST", "localhost")


# `True` if the user is running code in an iPython session.
# This is required to be able to use the viewer.
_IS_IPYTHON_SESSION = None


class Axis:
    def __init__(self) -> None:
        if not _is_ipython_session():
            raise RuntimeError("Tunnelvision can only be used in an IPython session within Chrome.")

        self.port = _get_first_available_port()
        self.process = None

    def show(self, x: np.ndarray, *, figsize: Tuple[int, int] = (514, 574), port=None):
        """Display a multi-dimensional array.

        Args:
            x (np.ndarray): The array to display.
            figsize (Tuple[int, int]): The figure size in pixels.
            port (int): The port to use for the viewer.
        """
        if not isinstance(x, np.ndarray):
            raise TypeError("Only numpy arrays are supported.")

        if x.ndim != 5:
            raise ValueError("Only 5-dimensional arrays are supported [BZYXC].")

        w, h = figsize
        if w <= 256 or h <= 256:
            raise ValueError("The figure size must be at least 256x256 pixels.")

        uri = f"http://{LOCALHOST_NAME}:{port or self.port}/ws"
        print(f"--- Opening viewer at {uri} ...")

        self.process = subprocess.Popen(
            ["tunnelvision", "--port", str(self.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Display the viewer
        display(IFrame(uri, width=w, height=h))

        return self


def show(x: np.ndarray, **kwargs):
    """Display a multi-dimensional array.

    Args:
        x (np.ndarray): The array to display.
    """
    ax = Axis()
    return ax.show(x, **kwargs)


def _is_ipython_session() -> bool:
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


def _get_first_available_port(initial: int = 49152, final: int = 65535) -> int:
    """Gets the first open port in a specified range of port numbers. Taken
    from https://github.com/gradio-app/gradio/blob/main/gradio/networking.py.
    More reading:
    https://stackoverflow.com/questions/19196105/how-to-check-if-a-network-port-is-open
    Args:
        initial: the initial value in the range of port numbers
        final: final (exclusive) value in the range of port numbers,
            should be greater than `initial`
    Returns:
        port: the first open port in the range
    """
    # rich.print(f"Trying to find an open port in ({initial}, {final}). ", end="")
    for port in range(initial, final):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create a socket object
            result = s.bind((LOCALHOST_NAME, port))  # Bind to the port  # noqa: F841
            s.close()
            # rich.print(f"Found open port: {port}")
            return port
        except OSError:
            pass

    raise OSError(
        "All ports from {} to {} are in use. Please close a port.".format(initial, final - 1)
    )
