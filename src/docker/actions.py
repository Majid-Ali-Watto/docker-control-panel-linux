"""
Docker Actions Module
High-level Docker service actions and bulk container/image/volume/network operations.
"""

import os
import time

from src.utils import platform_utils as plat
from src.utils.threads import startThreadForTask
from src.utils.utils import is_docker_running, docker_service_active, run_cmd, async_run
from src.config.config_manager import get_sudo_password
from tkinter import messagebox
from src.docker.commands import (
    DOCKER_START_ALL, DOCKER_STOP_ALL, DOCKER_RESTART_ALL,
    DOCKER_RM_ALL, DOCKER_RMI_ALL,
    DOCKER_VOLUME_PRUNE, DOCKER_VOLUME_LS_IDS, DOCKER_VOLUME_LS_DANGLING, DOCKER_VOLUME_RM_ALL,
    DOCKER_STOP_ALL_SAFE, DOCKER_RM_ALL_SAFE, DOCKER_RMI_ALL_SAFE, DOCKER_VOLUME_RM_ALL_SAFE,
    DOCKER_IMAGE_PRUNE, DOCKER_NETWORK_PRUNE
)


def check_docker_running():
    """Check if Docker is running and show warning if not"""
    if not is_docker_running():
        messagebox.showwarning("Docker Not Running", "Docker service is not running. Please start Docker first.")
        return False
    return True


def update_docker_status(root, status_var):
    """Update Docker service status"""
    if docker_service_active():
        status_var.set("Docker Status: Running ✅")
    else:
        status_var.set("Docker Status: Stopped ❌")


def _run_service_action(action):
    """Start / stop / restart the Docker daemon with this system's init system; the result text."""
    command = plat.service_command(action)
    if command is None:
        return plat.no_service_manager_text(action)
    return run_cmd(command, sudo=True, sudo_password=get_sudo_password())


def _have_root_password(root):
    """Starting / stopping the daemon needs root even for `docker`-group members, who are never
    asked for a password at startup: ask now (False when cancelled)."""
    if get_sudo_password() or os.geteuid() == 0 or plat.service_command("start") is None:
        return True
    from src.ui.ui_components import prompt_password_dialog
    return bool(prompt_password_dialog(root, None))


def _service_task(action, title, settle, root, status_var, show_loading_callback, show_text_output_callback):
    if not _have_root_password(root):
        show_text_output_callback(f"{title} Docker cancelled: controlling the Docker service needs your sudo password.")
        return

    def task():
        show_loading_callback(True)
        result = _run_service_action(action)
        show_loading_callback(False)
        show_text_output_callback(f"{title} Docker Result:\n{result}")
        time.sleep(settle)
        root.after(0, lambda: root.winfo_exists() and update_docker_status(root, status_var))
    startThreadForTask(task)


def start_docker_service(root, status_var, show_loading_callback, show_text_output_callback):
    """Start Docker service"""
    _service_task("start", "Start", 1, root, status_var, show_loading_callback, show_text_output_callback)


def stop_docker_service(root, status_var, show_loading_callback, show_text_output_callback):
    """Stop Docker service"""
    _service_task("stop", "Stop", 1, root, status_var, show_loading_callback, show_text_output_callback)


def restart_docker_service(root, status_var, show_loading_callback, show_text_output_callback):
    """Restart Docker service"""
    _service_task("restart", "Restart", 2, root, status_var, show_loading_callback, show_text_output_callback)


def bulk_output(show_text_output_callback, nothing_text):
    """Output callback for `docker <verb> $(docker ... -q)`: when the inner list is empty docker
    prints a usage error ("requires at least 1 argument"); show `nothing_text` instead."""
    def callback(result):
        show_text_output_callback(nothing_text if "requires at least 1 argument" in str(result) else result)
    return callback


def confirm_and_run(msg, cmd, show_text_output_callback, sudo=False, parent=None, show_loading_callback=None,
                    nothing_text=None):
    """Confirm action and run command (`nothing_text`: see bulk_output)"""
    from src.ui.ui_components import confirm_action_dialog
    if confirm_action_dialog(parent, "Confirm", msg):
        show = bulk_output(show_text_output_callback, nothing_text) if nothing_text else show_text_output_callback
        async_run(cmd, lambda r: show(r), sudo, get_sudo_password(),
                  loading_callback=show_loading_callback)


def clean_all_resources(show_text_output_callback, parent=None, show_loading_callback=None):
    """Clean all Docker resources"""
    from src.ui.ui_components import confirm_action_dialog
    msg = "This will:\n• Stop all containers\n• Delete all containers\n• Delete all images\n• Delete all volumes\n\nAre you sure?"
    if confirm_action_dialog(parent, "Clean All Resources", msg):
        if show_loading_callback:
            show_loading_callback(True)

        def done(r):
            if show_loading_callback:
                show_loading_callback(False)
            show_text_output_callback("All resources cleaned!")

        show_text_output_callback("Stopping all containers...\n")
        async_run(DOCKER_STOP_ALL_SAFE,
                 lambda r: async_run(DOCKER_RM_ALL_SAFE,
                                    lambda r: async_run(DOCKER_RMI_ALL_SAFE,
                                                       lambda r: async_run(DOCKER_VOLUME_RM_ALL_SAFE,
                                                                          done,
                                                                          sudo=True, sudo_password=get_sudo_password()),
                                                       sudo=True, sudo_password=get_sudo_password()),
                                    sudo=True, sudo_password=get_sudo_password()),
                 sudo=True, sudo_password=get_sudo_password())
