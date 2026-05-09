"""
Utilities Module
Common utility functions for Docker operations and checks.
"""

import subprocess
import threading
from src.utils.threads import startThreadForTask

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
    except:
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
        result = stdout + stderr
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
