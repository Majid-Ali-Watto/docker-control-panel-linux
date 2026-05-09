"""
Docker Actions Module
High-level Docker actions for containers, images, and volumes.
"""

from src.utils.threads import startThreadForTask
from src.utils.utils import is_docker_running, run_cmd, async_run
from src.config.config_manager import get_sudo_password
from tkinter import messagebox
from src.docker.docker_commands_constants import (
    DOCKER_START_ALL, DOCKER_STOP_ALL, DOCKER_RESTART_ALL, 
    DOCKER_RM_ALL, DOCKER_RMI_ALL,
    DOCKER_VOLUME_PRUNE, DOCKER_VOLUME_LS_IDS, DOCKER_VOLUME_LS_DANGLING, DOCKER_VOLUME_RM_ALL,
    DOCKER_STOP_ALL_SAFE, DOCKER_RM_ALL_SAFE, DOCKER_RMI_ALL_SAFE, DOCKER_VOLUME_RM_ALL_SAFE
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
        # Show result
        show_text_output_callback(f"Start Docker Result:\n{result}")
        # Wait a bit and then update status
        import time
        time.sleep(1)
        root.after(0, lambda: update_docker_status(root, status_var))
    startThreadForTask(task)
    


def stop_docker_service(root, status_var, show_loading_callback, show_text_output_callback):
    """Stop Docker service"""
    def task():
        show_loading_callback(True)
        result = run_cmd("systemctl stop docker.socket docker.service", sudo=True, sudo_password=get_sudo_password())
        show_loading_callback(False)
        # Show result
        show_text_output_callback(f"Stop Docker Result:\n{result}")
        # Wait a bit and then update status
        import time
        time.sleep(1)
        root.after(0, lambda: update_docker_status(root, status_var))
    startThreadForTask(task)
    


def restart_docker_service(root, status_var, show_loading_callback, show_text_output_callback):
    """Restart Docker service"""
    def task():
        show_loading_callback(True)
        result = run_cmd("systemctl restart docker.socket docker.service", sudo=True, sudo_password=get_sudo_password())
        show_loading_callback(False)
        # Show result
        show_text_output_callback(f"Restart Docker Result:\n{result}")
        # Wait a bit and then update status
        import time
        time.sleep(2)
        root.after(0, lambda: update_docker_status(root, status_var))
    startThreadForTask(task)
    


def confirm_and_run(msg, cmd, show_text_output_callback, sudo=False, parent=None, show_loading_callback=None):
    """Confirm action and run command"""
    from src.ui.ui_components import confirm_action_dialog
    if confirm_action_dialog(parent, "Confirm", msg):
        async_run(cmd, lambda r: show_text_output_callback(r), sudo, get_sudo_password(),
                  loading_callback=show_loading_callback)


# Container actions
def start_all_containers(show_text_output_callback, show_loading_callback=None):
    if not check_docker_running(): return
    from src.docker.docker_operations import run_docker_cmd
    run_docker_cmd(DOCKER_START_ALL, sudo=True, sudo_password=get_sudo_password(),
                   callback=show_text_output_callback, loading_callback=show_loading_callback)


def stop_all_containers(show_text_output_callback, show_loading_callback=None):
    if not check_docker_running(): return
    from src.docker.docker_operations import run_docker_cmd
    run_docker_cmd(DOCKER_STOP_ALL, sudo=True, sudo_password=get_sudo_password(),
                   callback=show_text_output_callback, loading_callback=show_loading_callback)


def restart_all_containers(show_text_output_callback, show_loading_callback=None):
    if not check_docker_running(): return
    from src.docker.docker_operations import run_docker_cmd
    run_docker_cmd(DOCKER_RESTART_ALL, sudo=True, sudo_password=get_sudo_password(),
                   callback=show_text_output_callback, loading_callback=show_loading_callback)


def delete_all_containers(show_text_output_callback, parent=None, show_loading_callback=None):
    if not check_docker_running(): return
    confirm_and_run("Delete ALL containers?", DOCKER_RM_ALL,
                   show_text_output_callback, sudo=True, parent=parent,
                   show_loading_callback=show_loading_callback)


# Image actions
def delete_all_images(show_text_output_callback, parent=None, show_loading_callback=None):
    if not check_docker_running(): return
    confirm_and_run("Delete ALL images?", DOCKER_RMI_ALL,
                   show_text_output_callback, sudo=True, parent=parent,
                   show_loading_callback=show_loading_callback)


# Volume actions
def prune_volumes(show_text_output_callback, parent=None, show_loading_callback=None):
    if not check_docker_running(): return
    confirm_and_run("Delete unused volumes?", DOCKER_VOLUME_PRUNE,
                   show_text_output_callback, sudo=True, parent=parent,
                   show_loading_callback=show_loading_callback)


def delete_used_volumes(show_text_output_callback, parent=None, show_loading_callback=None):
    """Delete volumes that are currently in use by containers"""
    if not check_docker_running(): return
    from src.ui.ui_components import confirm_action_dialog

    msg = "Delete all USED volumes?\nThis will remove volumes attached to containers."
    if confirm_action_dialog(parent, "Confirm", msg):
        def task():
            if show_loading_callback:
                show_loading_callback(True)
            all_volumes = run_cmd(DOCKER_VOLUME_LS_IDS).strip().split('\n')
            unused_result = run_cmd(DOCKER_VOLUME_LS_DANGLING).strip()
            unused_volumes = set(unused_result.split('\n')) if unused_result else set()
            used_volumes = [v for v in all_volumes if v and v not in unused_volumes]

            if not used_volumes:
                if show_loading_callback:
                    show_loading_callback(False)
                show_text_output_callback("No used volumes found.")
                return

            volumes_str = " ".join(used_volumes)
            result = run_cmd(f"docker volume rm {volumes_str}", sudo=True, sudo_password=get_sudo_password())
            if show_loading_callback:
                show_loading_callback(False)
            show_text_output_callback(f"Deleted used volumes:\n{result}")

        startThreadForTask(task)


def delete_all_volumes(show_text_output_callback, parent=None, show_loading_callback=None):
    """Delete all volumes (used and unused)"""
    if not check_docker_running(): return
    confirm_and_run("Delete ALL volumes (used and unused)?", DOCKER_VOLUME_RM_ALL,
                   show_text_output_callback, sudo=True, parent=parent,
                   show_loading_callback=show_loading_callback)


# Clean all resources
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
