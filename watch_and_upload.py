#!/usr/bin/env python3

"""
Inky Frame Watch and Upload Script (Python Edition)
Watches the local directory for changes and uploads modified files to the device.
"""

import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from types import FrameType

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# Colors for terminal output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"

# Configuration
PROJECT_DIR: str = os.path.dirname(os.path.abspath(__file__))
EXCLUDE_PATTERNS: list[str] = [
    r"\.git",
    r"\.venv",
    r"__pycache__",
    r"\.pyc",
    r"typings",
    r"\.ruff_cache",
    r"build",
    r"watch_and_upload\.sh",
    r"watch_and_upload\.py",
    r"\.mpremote\.pid",
]
DEBOUNCE_DELAY: float = 0.5  # seconds to wait for changes to settle
PID_FILE: str = os.path.join(PROJECT_DIR, ".mpremote.pid")
ERR_DEVICE_PORT_NOT_SET: str = "DEVICE_PORT is not set"

DEVICE_PORT: str | None = None
background_mpremote_proc: subprocess.Popen[bytes] | None = None
changed_files: set[str] = set()
timer: threading.Timer | None = None
lock: threading.Lock = threading.Lock()
fswatch_proc: subprocess.Popen[str] | None = None
cleanup_lock: threading.Lock = threading.Lock()
cleaned_up: bool = False


def log_info(msg: object) -> None:
    print(f"{BLUE}[INFO]{NC} {msg}")


def log_success(msg: object) -> None:
    print(f"{GREEN}[SUCCESS]{NC} {msg}")


def log_warning(msg: object) -> None:
    print(f"{YELLOW}[WARNING]{NC} {msg}")


def log_error(msg: object) -> None:
    print(f"{RED}[ERROR]{NC} {msg}")


def _extract_error_message(res: subprocess.CompletedProcess[str]) -> str:
    raw_err = res.stderr.strip() or res.stdout.strip()
    err_lines = [line.strip() for line in raw_err.splitlines() if line.strip()]
    return err_lines[-1] if err_lines else "Command failed"


def _run_with_progress(cmd: Sequence[str] | str, timeout: float) -> subprocess.CompletedProcess[str]:
    assert tqdm is not None
    with tqdm(total=timeout, desc="Sending command", unit="s", leave=False) as pbar:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        start_time = time.time()
        while proc.poll() is None:
            time.sleep(0.1)
            elapsed = time.time() - start_time
            pbar.n = min(round(elapsed, 1), float(timeout))
            pbar.refresh()
            if timeout and elapsed > timeout:
                proc.kill()
                out, err = proc.communicate()
                raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err)
        stdout, stderr = proc.communicate()
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def _execute_command(cmd: Sequence[str] | str, timeout: float) -> subprocess.CompletedProcess[str]:
    if tqdm is not None:
        return _run_with_progress(cmd, timeout)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout,
    )


def run_device_command(
    cmd: Sequence[str] | str,
    max_attempts: int = 3,
    base_delay: float = 1,
    timeout: float = 30,
) -> tuple[bool, str, str]:
    """Runs an mpremote command on the device with exponential retry and backoff."""
    cmd_str = shlex.join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
    delay = base_delay
    for attempt in range(1, max_attempts + 1):
        try:
            log_info(f"Sending command: {cmd_str}")
            res = _execute_command(cmd, timeout)
            if res.returncode == 0:
                return True, res.stdout, res.stderr
            err_msg = _extract_error_message(res)
        except subprocess.TimeoutExpired:
            err_msg = f"timed out after {timeout}s"
        except Exception as e:
            err_msg = str(e)

        if attempt < max_attempts:
            log_warning(f"Attempt {attempt}/{max_attempts} failed ({err_msg}), retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2

    return False, "", "All attempts failed"


def check_fswatch() -> None:
    """Checks if fswatch is installed."""
    try:
        subprocess.run(
            ["fswatch", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        log_error("fswatch is not installed. Install it with: brew install fswatch")
        sys.exit(1)


def detect_device() -> None:
    """Detects and connects to the MicroPython Board."""
    global DEVICE_PORT
    log_info("Detecting Inky Frame device...")

    try:
        res = subprocess.run(["mpremote", "devs"], capture_output=True, text=True, check=True)
        # Find MicroPython Board, exclude Adafruit, and extract device port
        for line in res.stdout.splitlines():
            if "MicroPython Board" in line and "Adafruit" not in line:
                match = re.search(r"(/dev/(?:tty|cu)[^\s]*)", line)
                if match:
                    DEVICE_PORT = match.group(1)
                    log_success(f"Device found at: {DEVICE_PORT}")
                    return

        log_error("No MicroPython Board found. Please connect your Inky Frame and ensure it's in USB mode.")
        log_error(f"Available devices:\n{res.stdout}")
        sys.exit(1)
    except Exception as e:
        log_error(f"Failed to detect device: {e}")
        sys.exit(1)


def kill_running_mpremote() -> None:
    """Kills any active background mpremote process started by this script."""
    global background_mpremote_proc
    if background_mpremote_proc is not None:
        log_info(f"Killing active mpremote process (PID: {background_mpremote_proc.pid})...")
        try:
            background_mpremote_proc.terminate()
            # Wait up to 3 seconds for it to exit
            for _ in range(6):
                if background_mpremote_proc.poll() is not None:
                    break
                time.sleep(0.5)

            if background_mpremote_proc.poll() is None:
                log_warning("Force killing mpremote process...")
                background_mpremote_proc.kill()
                background_mpremote_proc.wait()
        except Exception as e:
            log_warning(f"Error terminating mpremote process: {e}")
        finally:
            background_mpremote_proc = None


def kill_old_mpremote_pid_file() -> None:
    """Kills any leftover background mpremote processes from previous runs using the PID file."""
    pid_file = PID_FILE
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            log_info(f"Terminating old mpremote process from pid file (PID: {pid})...")
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
                # Check if still running, force kill
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        except Exception:
            pass
        try:
            os.remove(pid_file)
        except Exception:
            pass


def _get_port_pids(port: str) -> list[int]:
    try:
        res = subprocess.run(["lsof", "-t", port], capture_output=True, text=True, timeout=5)
        if res.returncode != 0 or not res.stdout.strip():
            return []
        current_pid = os.getpid()
        return [int(p) for p in res.stdout.strip().split() if int(p) != current_pid]
    except Exception:
        return []


def _signal_processes(pids: list[int], sig: int, action_name: str) -> None:
    for pid in pids:
        log_info(f"{action_name} process {pid} holding device port...")
        try:
            os.kill(pid, sig)
        except OSError:
            pass


def kill_processes_using_port() -> None:
    """Kills any other processes holding the serial device port open."""
    if not DEVICE_PORT:
        return
    pids = _get_port_pids(DEVICE_PORT)
    if not pids:
        return
    _signal_processes(pids, signal.SIGTERM, "Terminating")
    time.sleep(0.5)
    remaining_pids = _get_port_pids(DEVICE_PORT)
    if remaining_pids:
        _signal_processes(remaining_pids, signal.SIGKILL, "Force killing")
        time.sleep(0.5)


def stop_running_program() -> None:
    """Stops any running program on the device by issuing a reset."""
    kill_running_mpremote()
    kill_old_mpremote_pid_file()
    kill_processes_using_port()

    if not DEVICE_PORT:
        log_error(ERR_DEVICE_PORT_NOT_SET)
        return

    log_info("Stopping any running program on device...")
    success, _, err = run_device_command(["mpremote", "connect", DEVICE_PORT, "reset"], max_attempts=3, base_delay=1)
    if success:
        log_success("Program stopped")
    else:
        log_warning(f"Failed to stop program: {err}")

    # Wait for device port to settle and re-appear after reset
    for _ in range(10):
        if os.path.exists(DEVICE_PORT):
            break
        time.sleep(0.5)
    time.sleep(1)


def should_exclude(relative_path: str) -> bool:
    """Returns True if the path matches any of the exclude patterns."""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, relative_path):
            return True
    return False


def upload_file(file_path: str) -> None:
    """Uploads a single file to the device."""
    if not os.path.exists(file_path):
        return

    if not DEVICE_PORT:
        log_error(ERR_DEVICE_PORT_NOT_SET)
        return

    relative_path = os.path.relpath(file_path, PROJECT_DIR)
    if should_exclude(relative_path):
        return

    _, ext = os.path.splitext(file_path)
    if ext in [".py", ".json"]:
        log_info(f"Uploading: {relative_path}")
        target_path = f":{relative_path}"

        success, _, err = run_device_command(
            ["mpremote", "connect", DEVICE_PORT, "cp", file_path, target_path],
            max_attempts=5,
            base_delay=1,
        )
        if success:
            log_success(f"Uploaded: {relative_path}")
            time.sleep(1)
        else:
            log_error(f"Failed to upload: {relative_path} ({err})")
            time.sleep(1)


def run_main() -> None:
    """Runs main.py on the device in the background."""
    global background_mpremote_proc
    log_info("Running main.py on device...")
    time.sleep(1)

    try:
        if not DEVICE_PORT:
            log_error(ERR_DEVICE_PORT_NOT_SET)
            return
        # Run main.py in the background, allowing stdout/stderr to stream to the terminal
        background_mpremote_proc = subprocess.Popen(
            ["mpremote", "connect", DEVICE_PORT, "run", "main.py"],
            stdin=subprocess.DEVNULL,
        )
        log_success(f"main.py started (PID: {background_mpremote_proc.pid})")

        # Save PID to file for compatibility
        with open(PID_FILE, "w") as f:
            f.write(str(background_mpremote_proc.pid))
    except Exception as e:
        log_error(f"Failed to start main.py: {e}")


def initial_upload() -> None:
    """Performs initial upload of all necessary project files."""
    if not DEVICE_PORT:
        log_error(ERR_DEVICE_PORT_NOT_SET)
        return

    log_info("Performing initial upload of project files...")

    # Upload main.py
    main_py = os.path.join(PROJECT_DIR, "main.py")
    if os.path.exists(main_py):
        log_info("Uploading main.py...")
        success, _, err = run_device_command(
            ["mpremote", "connect", DEVICE_PORT, "cp", main_py, ":main.py"],
            max_attempts=5,
            base_delay=1,
        )
        if not success:
            log_error(f"Failed to upload main.py: {err}")
        time.sleep(1)

    # Folders to copy recursively
    dirs_to_upload = ["core", "apps", "models", "utils", "services"]
    for d in dirs_to_upload:
        dir_path = os.path.join(PROJECT_DIR, d)
        if os.path.isdir(dir_path):
            log_info(f"Uploading {d}/ directory...")
            success, _, err = run_device_command(
                ["mpremote", "connect", DEVICE_PORT, "cp", "-r", dir_path, f":{d}"],
                max_attempts=5,
                base_delay=1,
            )
            if not success:
                log_error(f"Failed to upload {d}/: {err}")
            time.sleep(1)

    # Upload secrets.py
    secrets_py = os.path.join(PROJECT_DIR, "secrets.py")
    if os.path.exists(secrets_py):
        log_info("Uploading secrets.py...")
        success, _, err = run_device_command(
            ["mpremote", "connect", DEVICE_PORT, "cp", secrets_py, ":secrets.py"],
            max_attempts=5,
            base_delay=1,
        )
        if not success:
            log_error(f"Failed to upload secrets.py: {err}")
        time.sleep(1)

    log_success("Initial upload complete")


def process_changes() -> None:
    """Callback function executed after the debounce period ends."""
    global timer
    with lock:
        files_to_upload = sorted(changed_files)
        changed_files.clear()
        timer = None

    if not files_to_upload:
        return

    log_info("Debounce period ended. Processing changes...")

    # Stop program
    stop_running_program()

    # Upload each modified file
    for file_path in files_to_upload:
        upload_file(file_path)

    # Restart program
    run_main()


def watch_changes() -> None:
    """Watches the directory for changes using fswatch."""
    global timer, fswatch_proc
    log_info(f"Watching for file changes in {PROJECT_DIR}")
    log_info("Press Ctrl+C to stop")

    cmd = [
        "fswatch",
        "-r",
        PROJECT_DIR,
        "--exclude",
        r"\.git",
        "--exclude",
        r"\.venv",
        "--exclude",
        r"__pycache__",
        "--exclude",
        r"\.pyc",
        "--exclude",
        r"typings",
        "--exclude",
        r"\.ruff_cache",
        "--exclude",
        r"build",
        "--exclude",
        r"watch_and_upload\.(sh|py)",
        "--event",
        "Updated",
        "--event",
        "Created",
        "--event",
        "Removed",
    ]

    try:
        fswatch_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

        if fswatch_proc.stdout is None:
            return

        while True:
            line = fswatch_proc.stdout.readline()
            if not line:
                break

            file_path = line.strip()
            if not file_path:
                continue

            relative_path = os.path.relpath(file_path, PROJECT_DIR)

            # Ignore non-python/non-json changes and excluded patterns early
            if should_exclude(relative_path):
                continue

            _, ext = os.path.splitext(file_path)
            if ext not in [".py", ".json"]:
                continue

            log_info(f"Change detected: {relative_path}")

            with lock:
                changed_files.add(file_path)
                if timer is not None:
                    timer.cancel()

                timer = threading.Timer(DEBOUNCE_DELAY, process_changes)
                timer.start()

    except Exception as e:
        log_error(f"fswatch watcher error: {e}")


def cleanup(signum: int | None = None, frame: FrameType | None = None) -> None:
    """Performs clean shutdown on termination."""
    global cleaned_up, timer, fswatch_proc
    with cleanup_lock:
        if cleaned_up:
            return
        cleaned_up = True

    print()  # Add a clean newline after Ctrl+C
    log_info("Cleaning up...")

    # Terminate fswatch
    if fswatch_proc is not None:
        try:
            fswatch_proc.terminate()
            fswatch_proc.wait(timeout=2)
        except Exception:
            try:
                fswatch_proc.kill()
            except Exception:
                pass

    # Cancel timer
    with lock:
        if timer is not None:
            timer.cancel()
            timer = None

    # Stop program on device
    try:
        stop_running_program()
    except Exception as e:
        log_error(f"Error during cleanup stop program: {e}")

    log_success("Cleanup complete")
    sys.exit(0)


# Set up signal handlers for SIGINT and SIGTERM
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def main() -> None:
    log_info("=== Inky Frame Watch and Upload Script (Python Edition) ===")

    check_fswatch()
    detect_device()

    # Stop any running program and ensure clean serial access before initial upload
    stop_running_program()

    initial_upload()

    run_main()
    watch_changes()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cleanup()
