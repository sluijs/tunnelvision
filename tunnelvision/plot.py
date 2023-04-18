import asyncio
import json
import os
import socket
from typing import Tuple

import numpy as np
import websockets
from IPython.display import display
from shortuuid import uuid

from tunnelvision.config import config
from tunnelvision.definitions import ROOT_DIR
from tunnelvision.server import start, state
from tunnelvision.utils import Viewport

__all__ = ["Axis", "show"]


# `True` if the user is running code in an iPython session.
# This is required to be able to use the viewer.
_IS_IPYTHON_SESSION = None


class Axis:
    def __init__(self, *, figsize: Tuple[int, int] = (512, 512)) -> None:
        if not _is_ipython_session():
            raise RuntimeError("Tunnelvision can only be used in an IPython session within Chrome.")

        # Start the server if it is not already running
        if not state.is_running:
            server_path = os.path.join(ROOT_DIR, "bin", "tunnelvision-server")
            state.port = (
                config.port if isinstance(config.port, int) else _get_first_available_port()
            )
            dist_path = os.path.join(ROOT_DIR, "bin", "dist")

            start(server_path, state.port, dist_path)

            # Ping the front-end client to make sure it is running
            # NB: this function will block until the server is ready or timeout
            # self._block_until_ready()

        # Wait for the front-end to connect to the server
        self.handshake = asyncio.Future()

        # Define the uri for the viewport
        h, w = figsize
        self.hash = uuid()
        self.uri = f"http://{config.hostname}:{state.port}"
        self.viewport = Viewport(self.uri, width=w + 62, height=h + 2, hash=self.hash, axis=self)

    def imshow(
        self,
        x: np.ndarray,
        *,
        metadata: dict = {},
        config: dict = {},
    ):
        """Display a multi-dimensional array.

        Args:
            x (np.ndarray): The array to display.
            figsize (Tuple[int, int]): The figure size in pixels.
            port (int): The port to use for the viewer.
        """
        if not isinstance(x, np.ndarray):
            raise TypeError("Only numpy arrays are supported.")

        if x.dtype not in [np.int8, np.int16, np.int32, np.uint8, np.uint16, np.uint32, np.float32]:
            raise TypeError("Supported dtypes are =< 32 bit (unsigned) integers/floating points")

        if x.ndim != 5:
            raise ValueError("Only 5-dimensional arrays are supported [BxZxHxWxC].")

        if state.process.poll() is not None:
            raise RuntimeError("Server has stopped running after Axis creation.")

        if self.handshake.done() and (self.handshake.cancelled() or self.handshake.exception()):
            raise RuntimeError("Handshake with front-end failed.")

        # Queue the array to be sent to the viewer
        task = asyncio.create_task(self._send_view(x=x, config=config, metadata=metadata))
        task.add_done_callback(self._send_callback)

        return self.viewport

    def show(self):
        """Display the Viewport."""

        display(self.viewport)

    def ping(self):
        request = b"HEAD / HTTP/1.1\r\nHost: server-url\r\n\r\n"
        with socket.create_connection(
            (config.hostname, state.port), timeout=config.timeout
        ) as sock:
            sock.sendall(request)
            response = sock.recv(1024)
            if response:
                return True
            else:
                raise TimeoutError(f"Server did not respond in {config.timeout} seconds.")

    async def _wait_for_handshake(self):
        """Wait for the front-end to connect to the server."""

        async def _handshake():
            uri = f"ws://{state.hostname}:{state.port}/ws"
            async with websockets.connect(uri) as websocket:
                # Wait for the front-end to connect
                # Do not timeout here, because the front-end can only connect after iframe loads
                while True:
                    try:
                        msg = await websocket.recv()
                        msg = json.loads(msg)

                        if msg.get("hash", None) == self.hash and msg.get("connected", False):
                            self.handshake.set_result(True)

                            await websocket.close(reason="--- verified handshake from Python")
                            break
                    except Exception as e:
                        self.handshake.set_exception(e)

        try:
            await asyncio.wait_for(_handshake(), timeout=config.timeout)
        except Exception as e:
            self.handshake.set_exception(e)
            print("Handshake with front-end failed.")

    async def _send_view(
        self,
        *,
        x: np.ndarray = None,
        config: dict = {},
        metadata: dict = {},
    ):
        """Send a WebSocket message to the front-end client."""

        uri = f"ws://{state.hostname}:{state.port}/ws"
        async with websockets.connect(uri) as websocket:
            try:
                # Wait for the front-end to connect to the server
                await self.handshake

                # Send the message in JSON forma
                msg = {
                    "hash": self.hash,
                    "config": config,
                    "metadata": metadata,
                }

                if isinstance(x, np.ndarray):
                    msg["shape"] = x.shape
                    msg["dtype"] = x.dtype.name

                await websocket.send(json.dumps(msg))

                # Send the array
                if isinstance(x, np.ndarray):
                    await websocket.send(self.hash.encode() + x.tobytes())

                await websocket.close(reason="--- sent view from Python")
                return True
            except Exception as e:
                self.handshake.set_exception(e)
                return False

    @staticmethod
    def _handshake_callback(task: asyncio.Task):
        if task.cancelled():
            raise RuntimeError("Could not complete handshake with front-end, task was cancelled.")

        if task.exception() is not None:
            raise task.exception()

    @staticmethod
    def _send_callback(task: asyncio.Task):
        if task.cancelled():
            raise RuntimeError("Could not send view to front-end, task was cancelled.")

        if task.exception() is not None:
            raise task.exception()


def show(x: np.ndarray, **kwargs):
    """Display a multi-dimensional array.

    Args:
        x (np.ndarray): The array to display.
    """
    ax = Axis()
    display(ax.imshow(x=x, **kwargs))


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


def _get_first_available_port(start: int = 49152, end: int = 65535) -> int:
    """Gets the first open port in a specified range of port numbers. Taken
    from https://github.com/gradio-app/gradio/blob/main/gradio/networking.py.
    More reading:
    https://stackoverflow.com/questions/19196105/how-to-check-if-a-network-port-is-open
    Args:
        start: the start value in the range of port numbers
        end: end (exclusive) value in the range of port numbers,
            should be greater than `start`
    Returns:
        port: the first open port in the range
    """
    for port in range(start, end):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create a socket object
            _ = s.bind((config.hostname, port))  # Bind to the port  # noqa: F841
            s.close()
            return port
        except OSError:
            pass

    raise OSError("All ports from {} to {} are in use. Please close a port.".format(start, end - 1))
