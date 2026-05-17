"""
Docker Actions Module
High-level Docker service actions and bulk container/image/volume/network operations.
"""

from src.utils.threads import startThreadForTask
from src.utils.utils import is_docker_running, run_cmd, async_run
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
    import subprocess
    status = subprocess.run(
        "systemctl is-active docker",
        shell=True,
        capture_output=True,
        text=True
    )
    if status.stdout.strip() == "active":
        status_var.set("Docker Status: Running ✅")
    else:
        status_var.set("Docker Status: Stopped ❌")


def start_docker_service(root, status_var, show_loading_callback, show_text_output_callback):
    """Start Docker service"""
    def task():
        show_loading_callback(True)
        result = run_cmd("systemctl start docker.socket docker.service", sudo=True, sudo_password=get_sudo_password())
        show_loading_callback(False)
        show_text_output_callback(f"Start Docker Result:\n{result}")
        import time
        time.sleep(1)
        root.after(0, lambda: root.winfo_exists() and update_docker_status(root, status_var))
    startThreadForTask(task)


def stop_docker_service(root, status_var, show_loading_callback, show_text_output_callback):
    """Stop Docker service"""
    def task():
        show_loading_callback(True)
        result = run_cmd("systemctl stop docker.socket docker.service", sudo=True, sudo_password=get_sudo_password())
        show_loading_callback(False)
        show_text_output_callback(f"Stop Docker Result:\n{result}")
        import time
        time.sleep(1)
        root.after(0, lambda: root.winfo_exists() and update_docker_status(root, status_var))
    startThreadForTask(task)


def restart_docker_service(root, status_var, show_loading_callback, show_text_output_callback):
    """Restart Docker service"""
    def task():
        show_loading_callback(True)
        result = run_cmd("systemctl restart docker.socket docker.service", sudo=True, sudo_password=get_sudo_password())
        show_loading_callback(False)
        show_text_output_callback(f"Restart Docker Result:\n{result}")
        import time
        time.sleep(2)
        root.after(0, lambda: root.winfo_exists() and update_docker_status(root, status_var))
    startThreadForTask(task)


def confirm_and_run(msg, cmd, show_text_output_callback, sudo=False, parent=None, show_loading_callback=None):
    """Confirm action and run command"""
    from src.ui.ui_components import confirm_action_dialog
    if confirm_action_dialog(parent, "Confirm", msg):
        async_run(cmd, lambda r: show_text_output_callback(r), sudo, get_sudo_password(),
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
