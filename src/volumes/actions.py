"""
Volume bulk actions (prune, delete used, delete all).
"""

from src.docker.actions import check_docker_running, confirm_and_run
from src.config.config_manager import get_sudo_password
from src.utils.utils import run_cmd
from src.utils.threads import startThreadForTask
from src.docker.commands import (
    DOCKER_VOLUME_PRUNE, DOCKER_VOLUME_LS_IDS, DOCKER_VOLUME_LS_DANGLING, DOCKER_VOLUME_RM_ALL,
    DOCKER_VOLUME_RM, DOCKER_PS_IDS_BY_VOLUME, DOCKER_CONTAINER_RM,
)
from src.shared.helpers import _quote, _join_quoted, is_error_output


def prune_volumes(show_text_output_callback, parent=None, show_loading_callback=None):
    if not check_docker_running(): return
    confirm_and_run("Delete every volume no container uses (named ones too)?\nTheir data is lost.",
                    DOCKER_VOLUME_PRUNE, show_text_output_callback, sudo=True, parent=parent,
                    show_loading_callback=show_loading_callback)


def delete_used_volumes(show_text_output_callback, parent=None, show_loading_callback=None):
    """Delete volumes that are in use. Docker refuses to remove a volume a container uses (even a
    stopped one), so those containers are force-removed first — the confirmation says so."""
    if not check_docker_running(): return
    from src.ui.ui_components import confirm_action_dialog

    msg = ("Delete all USED volumes?\n\nThe containers using them are removed first (running ones "
           "are stopped), then the volumes and their data.")
    if confirm_action_dialog(parent, "Confirm", msg):
        def task():
            if show_loading_callback:
                show_loading_callback(True)
            try:
                show_text_output_callback(_delete_used_volumes(get_sudo_password()))
            finally:
                if show_loading_callback:
                    show_loading_callback(False)

        startThreadForTask(task)


def _delete_used_volumes(sudo_pw):
    def run(cmd):
        return run_cmd(cmd, sudo=True, sudo_password=sudo_pw)

    listed = run(DOCKER_VOLUME_LS_IDS)
    unused = run(DOCKER_VOLUME_LS_DANGLING)
    for result in (listed, unused):
        if is_error_output(result):
            return f"Could not list volumes:\n{result}"
    unused_volumes = set(unused.split())
    used_volumes = [v for v in listed.split() if v not in unused_volumes]
    if not used_volumes:
        return "No used volumes found."

    containers = []
    for volume in used_volumes:
        for cid in run(DOCKER_PS_IDS_BY_VOLUME.format(volume=_quote(volume))).split():
            if cid not in containers:
                containers.append(cid)
    report = []
    if containers:
        removed = run(DOCKER_CONTAINER_RM.format(containers=_join_quoted(containers)))
        report.append(f"Removed containers:\n{removed}")
        if is_error_output(removed):
            return "\n\n".join(report)
    report.append(f"Deleted used volumes:\n{run(DOCKER_VOLUME_RM.format(volumes=_join_quoted(used_volumes)))}")
    return "\n\n".join(report)


def delete_all_volumes(show_text_output_callback, parent=None, show_loading_callback=None):
    """Delete all volumes (used and unused)"""
    if not check_docker_running(): return
    confirm_and_run("Delete ALL volumes?\nVolumes a container still uses are skipped by Docker "
                    "(use Delete Used for those).", DOCKER_VOLUME_RM_ALL,
                    show_text_output_callback, sudo=True, parent=parent,
                    show_loading_callback=show_loading_callback, nothing_text="No volumes to delete.")
