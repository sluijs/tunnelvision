from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml

from tunnelvision.utils import Singleton

__all__ = ["config", "Config"]


TUNNELVISION_CONFIG = os.getenv(
    "TUNNELVISION_CONFIG",
    os.path.join(os.path.expanduser("~"), ".cache", "tunnelvision", "default_config.yaml"),
)


@dataclass(frozen=True)
class Config(metaclass=Singleton):
    # The hostname to use for tunnelvision-server, defaults to localhost.
    hostname: str = "localhost"

    # The port to use for tunnelvision-server, defaults to the first available port.
    # NB: set this port when working with VS Code Remote.
    port: Optional[int] = None

    # How long to wait for the front-end to respond before giving up.
    timeout: int = 5

    # Paths to the stdout and stderr logs of tunnelvision-server.
    log_stdout: str = os.path.join(os.path.expanduser("~"), ".cache", "tunnelvision", "server.out")

    # Hydrate the config from a YAML file.
    def __post_init__(self):
        path = TUNNELVISION_CONFIG
        if not os.path.exists(path):
            # Create empty config
            os.makedirs(os.path.dirname(path), exist_ok=True)
            yaml.dump({}, open(path, "w"))

        config = yaml.load(open(path, "r"), Loader=yaml.FullLoader)
        self.__dict__.update(config)

        # Remove the logs
        if os.path.exists(self.log_stdout):
            os.remove(self.log_stdout)


config = Config()
