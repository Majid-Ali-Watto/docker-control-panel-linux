"""
Utilities Module
Common utility functions for Docker operations and checks.
"""

import os
import re
import shutil
import subprocess
import threading
from src.config.config_manager import get_setting
from src.utils import platform_utils as plat, terminals
from src.utils.platform_utils import clean_subprocess_env   # noqa: F401  (re-exported: callers import it from here)
from src.utils.threads import startThreadForTask

def installed_terminals():
    """Terminal emulators found on this system, in preference order."""
    return terminals.installed_terminals()


def check_terminal_installed():
    """The terminal emulator to use (the one chosen in Settings if installed, else the first
    available), or None when the system has none."""
    available = installed_terminals()
    chosen = get_setting("terminal")
    if chosen in available:
        return chosen
    return available[0] if available else None

# Global variable to track and cancel running operations
_current_operation = {'event': None}


def cancel_current_operation():
    """Cancel the currently running operation"""
    if _current_operation['event']:
        _current_operation['event'].set()


def engine():
    """The container CLI the app runs (Settings): 'docker' or 'podman'."""
    return get_setting("engine")


# `docker` where a command starts: at the beginning, after `$(`, or after ; & |
_DOCKER_WORD = re.compile(r"(^|\$\(|[;&|]\s*)docker(?= )")


def apply_engine(cmd):
    """Swap the leading `docker` of every command in `cmd` for the configured engine, so the
    command constants stay written once. Arguments such as image names are never touched."""
    name = engine()
    if name == "docker":
        return cmd
    return _DOCKER_WORD.sub(lambda m: m.group(1) + name, cmd)


def check_docker_installed():
    """Check that the container CLI is installed"""
    return shutil.which(engine()) is not None


def _engine_answers(name, timeout=15):
    """True when `<name> info` reaches a running daemon as this user."""
    try:
        result = subprocess.run([name, "info", "--format", "{{.ServerVersion}}"], capture_output=True,
                                text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def docker_service_active():
    """Whether the Docker daemon is up. systemd's view comes first; when it says no (or there is no
    systemd: Alpine, Void, WSL ...) `docker info` decides, which also covers snap / rootless
    installs and a remote `docker context`."""
    if plat.service_manager() == "systemd":
        status = subprocess.run(
            "systemctl is-active docker",
            shell=True,
            capture_output=True,
            text=True
        )
        if status.stdout.strip() == "active":
            return True
    return _engine_answers("docker", timeout=5)


def is_docker_running():
    """Check if Docker service is running (Podman has no daemon, so it always is)"""
    if engine() != "docker":
        return True
    return docker_service_active()


def docker_needs_sudo():
    """False when the current user can talk to the container engine directly (member of the
    `docker` group, rootless engine, ...), so no sudo password is needed for it."""
    try:
        result = subprocess.run(f"{engine()} info --format '{{{{.ServerVersion}}}}'", shell=True,
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return True
    return result.returncode != 0 or not result.stdout.strip()


def notify(title, message, root=None):
    """Desktop notification (notify-send) when enabled in Settings; skipped while the app window
    has focus (`root`), since the user is already looking at the result."""
    if not get_setting("notifications") or shutil.which("notify-send") is None:
        return False
    if root is not None:
        try:
            if root.focus_displayof() is not None:
                return False
        except Exception:
            pass
    try:
        subprocess.Popen(["notify-send", "--app-name=Docker Control Panel", title, message],
                         env=clean_subprocess_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    return True


def run_cmd(cmd, sudo=False, sudo_password=None, input_text=None):
    """Run a shell command and return output. `input_text` is fed to the command's stdin (after
    the sudo password, which sudo reads first) — used to pass secrets without putting them in argv."""
    cmd = apply_engine(cmd)
    if sudo and sudo_password:
        # Use sudo with -S flag to read password from stdin
        process = subprocess.Popen(
            f"sudo -S {cmd}",
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=f"{sudo_password}\n{input_text or ''}")
        clean_stderr = '\n'.join(
            line for line in stderr.splitlines()
            if not re.match(r'^\[sudo\]|^Password:|^Sorry,', line.strip(), re.IGNORECASE)
        ).strip()
        result = stdout if stdout.strip() or not clean_stderr else clean_stderr
        return result.strip()
    elif input_text is not None:
        result = subprocess.run(cmd, shell=True, input=input_text, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        return result.stdout.strip()
    else:
        try:
            result = subprocess.check_output(
                cmd,
                shell=True,
                stderr=subprocess.STDOUT,
                text=True
            )
            return result.strip()
        except subprocess.CalledProcessError as e:
            return e.output.strip()


def async_run(cmd, callback=None, sudo=False, sudo_password=None, loading_callback=None):
    """Run a command asynchronously in a thread with cancellation support"""
    # Cancel any previous operation
    cancel_current_operation()
    
    # Create new cancellation event
    cancel_event = threading.Event()
    _current_operation['event'] = cancel_event
    
    def task():
        if loading_callback:
            loading_callback(True)
        
        # Check if cancelled before running
        if not cancel_event.is_set():
            result = run_cmd(cmd, sudo, sudo_password)
            
            # Check if cancelled after running
            if not cancel_event.is_set() and callback:
                callback(result)
        
        if loading_callback:
            loading_callback(False)
        
        # Clear the operation if it's still this one
        if _current_operation['event'] is cancel_event:
            _current_operation['event'] = None
    
    startThreadForTask(task)
    


def sync_run(cmd, sudo=False, sudo_password=None, loading_callback=None):
    """Run a command synchronously and wait for completion"""
    if loading_callback:
        loading_callback(True)
    result = run_cmd(cmd, sudo, sudo_password)
    if loading_callback:
        loading_callback(False)
    return result


def parse_fixed_width_table(lines, header_line):
    """
    Parses docker-style fixed-width tables
    Split by 2 or more consecutive spaces
    """
    import re
    
    # Split header by 2+ spaces
    headers = re.split(r'  +', header_line.strip())
    
    rows = []
    for line in lines:
        if not line.strip():
            continue
        # Split each row by 2+ spaces
        row = re.split(r'  +', line.strip())
        rows.append(row)

    return headers, rows
