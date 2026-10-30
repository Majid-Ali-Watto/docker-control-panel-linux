"""
Docker Operations Module
Core Docker command execution and basic operations.
"""

import os
import signal
import subprocess

from src.utils import platform_utils as plat, shell
from src.utils.utils import async_run, apply_engine
from src.utils.threads import startThreadForTask


def run_docker_cmd(cmd, sudo=False, sudo_password=None, callback=None, loading_callback=None):
    """Run docker command with optional sudo"""
    async_run(cmd, callback, sudo=sudo, sudo_password=sudo_password, loading_callback=loading_callback)


def stream_docker_cmd(cmd, sudo=False, sudo_password=None, output_callback=None, complete_callback=None):
    """Run docker command asynchronously and stream combined stdout/stderr lines."""
    controller = {
        'process': None,
        'cancelled': False,
    }

    def task():
        cmd_ = apply_engine(cmd)
        with_sudo = bool(sudo and sudo_password and plat.uses_sudo())
        full_cmd = f"sudo -S {cmd_}" if with_sudo else cmd_
        options = dict(
            stdin=subprocess.PIPE if with_sudo else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        try:
            if plat.IS_WIN:
                process = shell.popen(full_cmd, new_group=True, **options)
            else:
                process = subprocess.Popen(full_cmd, shell=True, start_new_session=True, **options)
        except (OSError, shell.UnsupportedCommand) as exc:
            if complete_callback:
                complete_callback(str(exc), 1, False)
            return
        controller['process'] = process

        if with_sudo and process.stdin:
            process.stdin.write(f"{sudo_password}\n")
            process.stdin.flush()
            process.stdin.close()

        output_parts = []
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                output_parts.append(line)
                if output_callback:
                    output_callback(line)
            process.stdout.close()

        return_code = process.wait()
        if complete_callback:
            complete_callback(''.join(output_parts).strip(), return_code, controller['cancelled'])

    startThreadForTask(task)
    return controller


def cancel_stream(controller):
    """Cancel a streaming command started by stream_docker_cmd."""
    if not controller:
        return False

    process = controller.get('process')
    if not process or process.poll() is not None:
        return False

    controller['cancelled'] = True

    try:
        if plat.IS_WIN:
            process.terminate()     # no process groups to signal; this stops docker.exe itself
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except Exception:
        try:
            process.terminate()
        except Exception:
            return False

    return True


def show_table_command(cmd, columns, sudo=False, sudo_password=None, table_callback=None,
                      loading_callback=None, table_type=None, table_title=None, append=False):
    """Run docker command and show output in table"""
    def callback(result):
        rows = [line.split("\t") for line in result.splitlines() if line]
        if table_callback:
            table_callback(columns, rows, table_type, table_title, append)
    async_run(cmd, callback, sudo=sudo, sudo_password=sudo_password, loading_callback=loading_callback)
