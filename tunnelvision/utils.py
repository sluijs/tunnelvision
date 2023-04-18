import asyncio
from typing import Iterable, Union

from IPython.display import IFrame

__all__ = [
    "Singleton",
    "Viewport",
]


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Viewport(IFrame):
    def __init__(
        self,
        src: str,
        width: Union[int, str],
        height: Union[int, str],
        extras: Iterable[str] = None,
        axis=None,
        **kwargs,
    ):
        self.axis = axis
        super().__init__(src, width, height, extras, **kwargs)

    def _repr_html_(self):
        # TODO: see if we can move side-effect out of this method
        if self.axis:
            self.axis.handshake = asyncio.Future()
            task = asyncio.create_task(self.axis._wait_for_handshake())
            task.add_done_callback(self.axis._handshake_callback)

        return super()._repr_html_()

    def __repr__(self):
        return f"Viewport({self.src})"
