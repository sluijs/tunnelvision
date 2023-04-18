import atexit
import select
import subprocess
import threading

from tunnelvision.config import config
from tunnelvision.server.state import state

__all__ = ["start"]


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
    if isinstance(state.process, subprocess.Popen):
        print("Killing existing tunnelvision-server process...")
        state.process.terminate()
        state.process.wait()

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


def log_server_output(process: subprocess.Popen):
    if config.log_stdout:
        stdout_file = open(config.log_stdout, "wb", 0)

    if config.log_stderr:
        stderr_file = open(config.log_stderr, "wb", 0)

    while process.poll() is None:
        ready, _, _ = select.select([process.stdout], [], [], 0)
        line = process.stdout.readline().decode().strip()

        if config.log_stdout:
            stdout_file.write(line.encode() + b"\n")

        if config.log_stderr:
            stderr_file.write(line.encode() + b"\n")

    stdout_file.flush()
    stderr_file.flush()
    process.wait()
    stdout_file.close()
    stderr_file.close()


def exit():
    if isinstance(state.process, subprocess.Popen):
        state.process.terminate()
        state.process.wait()

    if isinstance(state.log_thread, threading.Thread) and state.log_thread.is_alive():
        state.log_thread.join()


atexit.register(exit)
