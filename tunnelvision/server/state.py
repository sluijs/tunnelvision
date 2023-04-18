import subprocess
import threading
from dataclasses import dataclass

from tunnelvision.config import config
from tunnelvision.utils import Singleton

__all__ = ["state", "State"]


@dataclass(frozen=False)
class State(metaclass=Singleton):
    # The process of tunnelvision-server
    process: "subprocess.Popen" = None

    # Hostname of tunnelvision-server
    hostname: str = config.hostname

    # The port tunnelvision-server is currently running on
    port: int = None

    # Timeout for tunnelvision-server
    timeout: int = config.timeout

    # Log thread for tunnelvision-server
    log_thread: "threading.Thread" = None

    @property
    def is_running(self) -> bool:
        if isinstance(self.process, subprocess.Popen):
            if self.process.poll() is None:
                return True

        return False


state = State()
