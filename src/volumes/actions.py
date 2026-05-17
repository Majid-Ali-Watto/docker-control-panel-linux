"""
Volume bulk actions (prune, delete used, delete all).
"""

from src.docker.actions import check_docker_running, confirm_and_run
from src.config.config_manager import get_sudo_password
from src.utils.utils import run_cmd
from src.utils.threads import startThreadForTask
from src.docker.commands import (
    DOCKER_VOLUME_PRUNE, DOCKER_VOLUME_LS_IDS, DOCKER_VOLUME_LS_DANGLING, DOCKER_VOLUME_RM_ALL,
)


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
            sudo_pw = get_sudo_password()
            all_volumes = run_cmd(DOCKER_VOLUME_LS_IDS, sudo=True, sudo_password=sudo_pw).strip().split('\n')
            unused_result = run_cmd(DOCKER_VOLUME_LS_DANGLING, sudo=True, sudo_password=sudo_pw).strip()
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
