import asyncio
import json
from typing import Tuple

import numpy as np
from IPython.display import IFrame, display
from shortuuid import uuid

from tunnelvision.config import config
from tunnelvision.server import auto_connect, auto_start, send_message, state
from tunnelvision.utils import handle_task_exception, is_ipython_session

__all__ = ["Axes", "imshow", "show"]


class Axes:
    def __init__(self, *, figsize: Tuple[int, int] = (512, 512)) -> None:
        """Create a 2D plot.

        Args:
            figsize (Tuple[int, int], optional): The size of the plot. Defaults to (512, 512).
                Plot dimensions are in pixels, and do not include the toolbar.
        """
        if not is_ipython_session():
            raise RuntimeError("Tunnelvision can only be used in an IPython session.")

        if not state.is_running:
            auto_start()

        if state.websocket is None:
            task = asyncio.create_task(auto_connect())
            task.add_done_callback(handle_task_exception)

        # Create a handshake for clients
        self._hash = uuid()
        self._handshake = asyncio.Future()
        state.handshakes[self._hash] = self._handshake

        # Add the handshake to the queue
        self._queue = asyncio.Queue()
        self._consumer = None

        # Define the uri for the viewport
        h, w = figsize
        self.uri = f"http://{config.hostname}:{state.port}"
        self._viewport = IFrame(self.uri, width=w + 62, height=h + 2, hash=self._hash)

    def imshow(
        self,
        x: np.ndarray,
        *,
        config: dict = {},
        cmap: str = None,
        metadata: dict = {},
        **kwargs,
    ):
        """Display a multi-dimensional array.

        Args:
            x (np.ndarray): The 5D array to display.
            config (dict, optional): The configuration for the viewport. Defaults to {}.
            cmap (str, optional): The colormap to use. Defaults to None. Use `seg` for segmentation.
            metadata (dict, optional): The metadata for the viewport. Defaults to {}.
        """
        if hasattr(x, "__tunnelvision__"):
            x, kwargs = x.__tunnelvision__(config=config, cmap=cmap, metadata=metadata, **kwargs)
        else:
            x = np.asarray(x)

        if x.dtype not in [np.int8, np.int16, np.int32, np.uint8, np.uint16, np.uint32, np.float32]:
            raise TypeError("Supported dtypes are =< 32 bit (unsigned) integers/floating points")

        if x.ndim != 5:
            raise ValueError("Only 5-dimensional arrays are supported [BxZxHxWxC].")

        if state.process.poll() is not None:
            raise RuntimeError("Server has stopped running after Axes creation.")

        if cmap is not None:
            # TODO: Add support for other built-in colormaps, random colormaps, and custom colormaps
            if cmap not in ["seg"]:
                raise ValueError(
                    f"Colormap {cmap} is not supported. Hint: use `seg` for segmentation maps."
                )

            config = {**config, "mode": "lut"}

        # Queue the array to be send to the viewer
        task = asyncio.create_task(self._produce(x=x, config=config, metadata=metadata))
        task.add_done_callback(handle_task_exception)

        return self

    def show(self):
        """Display the Viewport."""

        display(self)

    async def _produce(
        self,
        *,
        x: np.ndarray = None,
        config: dict = {},
        metadata: dict = {},
    ):
        """Send a multi-dimensional array to the viewport.

        Args:
            x (np.ndarray, optional): The 5D array to display. Defaults to None.
            config (dict, optional): The configuration for the viewport. Defaults to {}.
            metadata (dict, optional): The metadata for the viewport. Defaults to {}.
        """
        # Wait for the handshake to complete
        await self._handshake

        # Send the header
        key = uuid()
        msg = {
            "hash": self._hash,
            "key": key,
            "config": config,
            "metadata": metadata,
        }

        if isinstance(x, np.ndarray):
            msg["shape"] = x.shape
            msg["dtype"] = x.dtype.name

        self._queue.put_nowait(send_message(json.dumps(msg)))

        # Send the array (hash + key + array)
        if isinstance(x, np.ndarray):
            self._queue.put_nowait(send_message(self._hash.encode() + key.encode() + x.tobytes()))

        # Start the consumer if it is not already running
        if self._consumer is None or self._consumer.done():
            self._consumer = asyncio.create_task(self._consume())
            self._consumer.add_done_callback(handle_task_exception)

    async def _consume(self):
        """Consume the queue."""

        while state.websocket.open and not self._queue.empty():
            task = await self._queue.get()
            await task

            self._queue.task_done()

    def _repr_html_(self):
        """Display the Viewport."""

        return self._viewport._repr_html_()

    def __repr__(self) -> str:
        """Return a string representation of the Axes."""
        nl = "\n"
        nltb = "\n  "
        return (
            f"{self.__class__.__name__}({nltb}uri={self.uri}?hash={self._hash},{nltb}"
            f"height={self._viewport.height - 14},{nltb}width={self._viewport.width - 74},{nl})"
        )


def imshow(x: np.ndarray, ax: Axes = None, **kwargs):
    """Display a multi-dimensional array.

    Args:
        x (np.ndarray): The array to display.
        ax: The Axes object to use.
    """
    if ax is None:
        ax = Axes()

    ax.imshow(x=x, **kwargs)
    return ax


def show(x: np.generic, ax: Axes = None, **kwargs):
    """Display a multi-dimensional array.

    Args:
        x (np.generic): The array to display.
        ax: The Axes object to use.
    """

    display(imshow(x=x, ax=ax, **kwargs))
