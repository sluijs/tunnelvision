import asyncio
import json
import os
import socket
import subprocess
import time
from typing import Tuple

import numpy as np
import websockets
from IPython.display import IFrame, display

from tunnelvision.definitions import ROOT_DIR

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
        self.server_path = os.path.join(ROOT_DIR, "bin/tunnelvision-server")
        self.dist_path = os.path.join(ROOT_DIR, "bin/dist")
        self.process = None

    def show(
        self,
        x: np.ndarray,
        *,
        figsize: Tuple[int, int] = (512, 512),
        port=None,
    ):
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

        h, w = figsize
        if w <= 256 or h <= 256:
            raise ValueError("The figure size must be at least 256x256 pixels.")

        uri = f"http://{LOCALHOST_NAME}:{port or self.port}?port={port or self.port}"
        self.process = subprocess.Popen(
            [self.server_path, "--port", str(self.port), "-d", str(self.dist_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Display the viewer
        display(IFrame(uri, width=w + 62, height=h + 2))

        # Wait for the server to start, and send  the array
        ws_uri = f"ws://{LOCALHOST_NAME}:{port or self.port}/ws"
        _ = asyncio.create_task(_send_array(x, ws_uri))

        # Return the object with the process, so that it can be closed
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


async def _send_array(x: np.ndarray, uri: str, timeout: int = 5, interval: int = 0.1):
    # TODO: establish a handshake between the frontend client through the backend server
    # For now, we just wait a bit and hope that the *front-end* has loaded and is ready to receive
    # the array through the websocket.
    time.sleep(0.25)

    # TODO: ping the server to see if it is ready to receive the array
    start_time = time.time()
    while True:
        # Try to send the array, and if it fails, wait a bit and try again
        try:
            async with websockets.connect(uri) as websocket:
                # Send the header with a prefix signaling that it is JSON
                header = "JSON" + json.dumps({"shape": x.shape, "dtype": x.dtype.name})
                header = header.encode("utf-8")
                await websocket.send(header)

                # Send the array
                await websocket.send(x.tobytes())
                await websocket.close(reason="Goodbye!")

            # Break out of the loop, since the array was sent
            break

        except ConnectionRefusedError:
            pass

        if time.time() - start_time > timeout:
            raise TimeoutError("The server did not start in time.")

        time.sleep(interval)
