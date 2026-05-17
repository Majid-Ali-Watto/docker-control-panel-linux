"""
Utilities Module
Common utility functions for Docker operations and checks.
"""

import os
import re
import subprocess
import threading
from src.utils.threads import startThreadForTask

# Terminals tried in preference order
_KNOWN_TERMINALS = [
    'tilix', 'gnome-terminal', 'x-terminal-emulator',
    'xfce4-terminal', 'konsole', 'mate-terminal', 'terminator', 'xterm',
]


def clean_subprocess_env():
    """Return os.environ with snap-injected overrides stripped.

    When the app runs inside VS Code (snap), GTK/GIO/GDK vars point at
    snap-internal paths that break system binaries like tilix/gnome-terminal
    with a libpthread symbol error.  Removing them lets each binary find its
    own runtime libraries from the system prefix.
    """
    _DROP = {
        'GDK_PIXBUF_MODULEDIR', 'GDK_PIXBUF_MODULE_FILE',
        'GIO_MODULE_DIR', 'GSETTINGS_SCHEMA_DIR',
        'GTK_EXE_PREFIX', 'GTK_IM_MODULE_FILE', 'GTK_PATH',
        'LOCPATH', 'GIO_LAUNCHED_DESKTOP_FILE',
    }
    env = {k: v for k, v in os.environ.items()
           if k not in _DROP and 'SNAP' not in k}
    # Strip snap dirs from PATH
    env['PATH'] = ':'.join(
        p for p in env.get('PATH', '').split(':') if '/snap/' not in p
    ) or '/usr/bin:/usr/local/bin:/bin'
    return env


def check_terminal_installed():
    """Return the name of the first available terminal emulator, or None."""
    import shutil
    for term in _KNOWN_TERMINALS:
        if shutil.which(term):
            return term
    return None

# Global variable to track and cancel running operations
_current_operation = {'event': None}


def cancel_current_operation():
    """Cancel the currently running operation"""
    if _current_operation['event']:
        _current_operation['event'].set()


def check_docker_installed():
    """Check if Docker is installed"""
    try:
        result = subprocess.run(
            ["which", "docker"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def is_docker_running():
    """Check if Docker service is running"""
    status = subprocess.run(
        "systemctl is-active docker",
        shell=True,
        capture_output=True,
        text=True
    )
    return status.stdout.strip() == "active"


def run_cmd(cmd, sudo=False, sudo_password=None):
    """Run a shell command and return output"""
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
        stdout, stderr = process.communicate(input=f"{sudo_password}\n")
        clean_stderr = '\n'.join(
            line for line in stderr.splitlines()
            if not re.match(r'^\[sudo\]|^Password:|^Sorry,', line.strip(), re.IGNORECASE)
        ).strip()
        result = stdout if stdout.strip() or not clean_stderr else clean_stderr
        return result.strip()
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
