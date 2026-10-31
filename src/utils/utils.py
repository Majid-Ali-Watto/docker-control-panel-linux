"""
Utilities Module
Common utility functions for Docker operations and checks.
"""

import os
import re
import shlex
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
    if result.returncode == 0 and result.stdout.strip():
        return False
    # No answer. A stopped daemon must not mean "ask for sudo": membership of the `docker` group
    # (which grants the socket) decides then; a refused socket always needs sudo.
    refused = "permission denied" in str(result.stderr or "").lower()
    return refused or engine() != "docker" or not _in_docker_group()


def _in_docker_group():
    import grp
    try:
        return any(grp.getgrgid(gid).gr_name == "docker" for gid in os.getgroups())
    except (KeyError, OSError):
        return False


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


class CmdOutput(str):
    """Command output (a str) that also carries the command's exit status in `returncode`."""
    returncode = None


def _output(result, strip_sudo=False):
    """What a command printed: stdout when it succeeded (its stderr only when stdout is empty, e.g.
    `compose up` progress), so docker's WARNING lines never land in parsed output; both when it
    failed, so the reason is never lost."""
    stderr = result.stderr or ''
    if strip_sudo:
        stderr = '\n'.join(line for line in stderr.splitlines() if not _SUDO_NOISE.match(line.strip()))
    stdout, stderr = (result.stdout or '').strip(), stderr.strip()
    if result.returncode == 0:
        text = stdout or stderr
    else:
        text = '\n'.join(part for part in (stdout, stderr) if part)
    out = CmdOutput(text)
    out.returncode = result.returncode
    return out


# sudo's own lines (wrong password retries); its prompt is silenced with -p ''
_SUDO_NOISE = re.compile(r'^\[sudo\]|^Password:|^Sorry, try again', re.IGNORECASE)


def sudo_command(cmd):
    """`cmd` run by a root shell, so `$(...)`, pipes and redirects inside it run as root too (a
    bare `sudo -S docker stop $(docker ps -q)` expands the `$(...)` as the user, who may not reach
    the docker socket). -k makes sudo always read the password line from stdin (with cached
    credentials it would pass that line on to the command); -p '' keeps its prompt out of the output."""
    return f"sudo -S -k -p '' sh -c {shlex.quote(cmd)}"


def run_cmd(cmd, sudo=False, sudo_password=None, input_text=None):
    """Run a shell command and return its output (see _output) as a CmdOutput, whose `returncode`
    is the exit status. `input_text` is fed to the command's stdin (after the sudo password, which
    sudo reads first) — used to pass secrets without putting them in argv."""
    cmd = apply_engine(cmd)
    if sudo and sudo_password:
        result = subprocess.run(sudo_command(cmd), shell=True, input=f"{sudo_password}\n{input_text or ''}",
                                capture_output=True, text=True)
        return _output(result, strip_sudo=True)
    result = subprocess.run(cmd, shell=True, input=input_text, capture_output=True, text=True)
    return _output(result)


def async_run(cmd, callback=None, sudo=False, sudo_password=None, loading_callback=None, cancellable=True):
    """Run a command in a thread. A cancellable run (loading a view) is dropped when a newer one
    starts or the view changes, so a stale list never replaces the current one. Commands that
    change state pass cancellable=False: their result (status, list reload) must always arrive."""
    cancel_event = threading.Event()
    if cancellable:
        cancel_current_operation()
        _current_operation['event'] = cancel_event

    def task():
        if loading_callback:
            loading_callback(True)
        try:
            if not cancel_event.is_set():
                result = run_cmd(cmd, sudo, sudo_password)
                if not cancel_event.is_set() and callback:
                    callback(result)
        finally:
            # a cancelled run leaves the spinner to the run that replaced it, if there is one
            replaced = _current_operation['event'] not in (None, cancel_event)
            if loading_callback and not (cancel_event.is_set() and replaced):
                loading_callback(False)
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
