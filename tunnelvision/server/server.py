import asyncio
import atexit
import json
import os
import select
import subprocess
import threading

import websockets

from tunnelvision.config import config
from tunnelvision.definitions import ROOT_DIR
from tunnelvision.server.state import state

__all__ = ["auto_start", "start", "connect", "wait_for_handshake", "send_message"]


def auto_start():
    server_path = os.path.join(ROOT_DIR, "bin", "tunnelvision-server")
    state.port = config.port
    dist_path = os.path.join(ROOT_DIR, "bin", "dist")

    start(server_path, state.port, dist_path)


def start(
    server_path: str,
    port: int,
    dist_path: str,
) -> subprocess.Popen:
    """Starts the tunnelvision-server.

    Args:
        server_path (str): The path to the tunnelvision-server executable.
        port (int): The port to use for tunnelvision-server.
        dist_path (str): The path to the tunnelvision-server dist folder.

    Returns:
        subprocess.Popen: The process object for the tunnelvision-server.
    """
    state.port = port

    state.process = subprocess.Popen(
        [server_path, "--port", str(port), "-d", str(dist_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    ready, _, _ = select.select([state.process.stdout], [], [], config.timeout)
    if ready:
        # Read the line from stdout
        line = state.process.stdout.readline().decode().strip()
        if "--- tunnelvision ---" in line:
            if config.log_stdout or config.log_stderr:
                state.log_thread = threading.Thread(target=log_server_output, args=(state.process,))
                state.log_thread.start()
    else:
        # Timeout occurred
        raise TimeoutError("Timed out waiting for server to start.")

    return state.process


async def auto_connect() -> "asyncio.Task":
    connection = asyncio.create_task(connect())
    if state.handshake_task is not None:
        state.handshake_task.cancel()

    state.handshake_task = asyncio.create_task(wait_for_handshake(connection))
    return connection


async def connect() -> websockets.WebSocketClientProtocol:
    """Connects to the tunnelvision-server.

    Returns:
        websockets.WebSocketClientProtocol: The websocket connection to the tunnelvision-server.
    """
    if state.process is None:
        raise Exception("Server is not running, run `start()` first.")

    uri = f"ws://{state.hostname}:{state.port}/ws"
    state.websocket = await websockets.connect(uri, open_timeout=state.timeout)

    return state.websocket


async def wait_for_handshake(task: asyncio.Task):
    """Waits for the handshake to complete."""

    if state.process is None:
        raise Exception("Server is not running, run `start()` first.")

    await asyncio.wait_for(task, state.timeout)
    if not isinstance(state.websocket, websockets.WebSocketClientProtocol):
        raise Exception("Websocket client not connected, run `connect()` first.")

    while not state.websocket.closed:
        try:
            msg = await state.websocket.recv()
            msg = json.loads(msg)

            if "hash" in msg and "connected" in msg:
                if msg["hash"] not in state.handshakes:
                    state.handshakes[msg["hash"]] = asyncio.Future()

                state.handshakes[msg["hash"]].set_result(msg["connected"])

        except Exception:
            pass


async def send_message(message):
    """Send a text or binary message to the websocket."""

    if isinstance(state.websocket, websockets.WebSocketClientProtocol) and state.websocket.open:
        await state.websocket.send(message)
    else:
        raise RuntimeError("Could not send message, websocket is not open.")


def log_server_output(process: subprocess.Popen):
    if config.log_stdout:
        stdout_file = open(config.log_stdout, "wb", 0)

    while process.poll() is None:
        ready, _, _ = select.select([process.stdout], [], [], 0)
        if not ready:
            continue

        line = process.stdout.readline().decode().strip()
        if config.log_stdout:
            stdout_file.write(line.encode() + b"\n")

    stdout_file.flush()
    process.wait()
    stdout_file.close()


def _close():
    if isinstance(state.process, subprocess.Popen):
        state.process.terminate()
        state.process.wait()

    if isinstance(state.log_thread, threading.Thread) and state.log_thread.is_alive():
        state.log_thread.join()

    if isinstance(state.websocket, websockets.WebSocketClientProtocol):
        state.websocket.close()

    if isinstance(state.handshake_task, asyncio.Task) and not state.handshake_task.done():
        state.handshake_task.cancel()


atexit.register(_close)
