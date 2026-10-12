#!/usr/bin/env python3

"""
Inky Frame Watch and Upload Script (Python Edition)
Watches the local directory for changes and uploads modified files to the device.
"""

import os
import sys
import time
import signal
import subprocess
import threading
import re

# Colors for terminal output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"

# Configuration
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
EXCLUDE_PATTERNS = [
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
DEBOUNCE_DELAY = 0.5  # seconds to wait for changes to settle
PID_FILE = os.path.join(PROJECT_DIR, ".mpremote.pid")

DEVICE_PORT = None
background_mpremote_proc = None
changed_files = set()
timer = None
lock = threading.Lock()
fswatch_proc = None
cleanup_lock = threading.Lock()
cleaned_up = False


def log_info(msg):
    print(f"{BLUE}[INFO]{NC} {msg}")


def log_success(msg):
    print(f"{GREEN}[SUCCESS]{NC} {msg}")


def log_warning(msg):
    print(f"{YELLOW}[WARNING]{NC} {msg}")


def log_error(msg):
    print(f"{RED}[ERROR]{NC} {msg}")


def run_device_command(cmd, max_attempts=3, base_delay=1):
    """Runs an mpremote command on the device with exponential retry and backoff."""
    attempt = 1
    delay = base_delay
    while attempt <= max_attempts:
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL
            )
            if res.returncode == 0:
                return True, res.stdout, res.stderr

            err_msg = res.stderr.strip() or res.stdout.strip()
            if attempt < max_attempts:
                log_warning(
                    f"Attempt {attempt}/{max_attempts} failed ({err_msg}), retrying in {delay}s..."
                )
                time.sleep(delay)
                delay *= 4
        except Exception as e:
            if attempt < max_attempts:
                log_warning(
                    f"Attempt {attempt}/{max_attempts} error ({e}), retrying in {delay}s..."
                )
                time.sleep(delay)
                delay *= 4
        attempt += 1

    return False, "", "All attempts failed"


def check_fswatch():
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


def detect_device():
    """Detects and connects to the MicroPython Board."""
    global DEVICE_PORT
    log_info("Detecting Inky Frame device...")

    try:
        res = subprocess.run(
            ["mpremote", "devs"], capture_output=True, text=True, check=True
        )
        # Find MicroPython Board, exclude Adafruit, and extract device port
        for line in res.stdout.splitlines():
            if "MicroPython Board" in line and "Adafruit" not in line:
                match = re.search(r"(/dev/(?:tty|cu)[^\s]*)", line)
                if match:
                    DEVICE_PORT = match.group(1)
                    log_success(f"Device found at: {DEVICE_PORT}")
                    return

        log_error(
            "No MicroPython Board found. Please connect your Inky Frame and ensure it's in USB mode."
        )
        log_error(f"Available devices:\n{res.stdout}")
        sys.exit(1)
    except Exception as e:
        log_error(f"Failed to detect device: {e}")
        sys.exit(1)


def kill_running_mpremote():
    """Kills any active background mpremote process started by this script."""
    global background_mpremote_proc
    if background_mpremote_proc is not None:
        log_info(
            f"Killing active mpremote process (PID: {background_mpremote_proc.pid})..."
        )
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


def kill_old_mpremote_pid_file():
    """Kills any leftover background mpremote processes from previous runs using the PID file."""
    pid_file = PID_FILE
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            log_info(f"Killed old mpremote process from pid file (PID: {pid})")
        except Exception:
            pass
        try:
            os.remove(pid_file)
        except Exception:
            pass


def stop_running_program():
    """Stops any running program on the device by issuing a reset."""
    kill_running_mpremote()
    kill_old_mpremote_pid_file()

    log_info("Stopping any running program on device...")
    success, _, err = run_device_command(
        ["mpremote", "connect", DEVICE_PORT, "reset"], max_attempts=3, base_delay=1
    )
    if success:
        log_success("Program stopped")
    else:
        log_warning(f"Failed to stop program: {err}")
    time.sleep(2)


def should_exclude(relative_path):
    """Returns True if the path matches any of the exclude patterns."""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, relative_path):
            return True
    return False


def upload_file(file_path):
    """Uploads a single file to the device."""
    if not os.path.exists(file_path):
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


def run_main():
    """Runs main.py on the device in the background."""
    global background_mpremote_proc
    log_info("Running main.py on device...")
    time.sleep(1)

    try:
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


def initial_upload():
    """Performs initial upload of all necessary project files."""
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


def process_changes():
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


def watch_changes():
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
        fswatch_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )

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


def cleanup(signum=None, frame=None):
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


def main():
    log_info("=== Inky Frame Watch and Upload Script (Python Edition) ===")

    check_fswatch()
    detect_device()

    # Initial upload (don't stop program - device might not be running anything yet)
    initial_upload()

    run_main()
    watch_changes()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cleanup()
