"""
Bulk container actions (start/stop/restart/delete all).
"""

from src.docker.actions import check_docker_running, confirm_and_run
from src.docker.operations import run_docker_cmd
from src.config.config_manager import get_sudo_password
from src.docker.commands import (
    DOCKER_START_ALL, DOCKER_STOP_ALL, DOCKER_RESTART_ALL, DOCKER_RM_ALL,
)


def start_all_containers(show_text_output_callback, show_loading_callback=None):
    if not check_docker_running(): return
    run_docker_cmd(DOCKER_START_ALL, sudo=True, sudo_password=get_sudo_password(),
                   callback=show_text_output_callback, loading_callback=show_loading_callback)


def stop_all_containers(show_text_output_callback, show_loading_callback=None):
    if not check_docker_running(): return
    run_docker_cmd(DOCKER_STOP_ALL, sudo=True, sudo_password=get_sudo_password(),
                   callback=show_text_output_callback, loading_callback=show_loading_callback)


def restart_all_containers(show_text_output_callback, show_loading_callback=None):
    if not check_docker_running(): return
    run_docker_cmd(DOCKER_RESTART_ALL, sudo=True, sudo_password=get_sudo_password(),
                   callback=show_text_output_callback, loading_callback=show_loading_callback)


def delete_all_containers(show_text_output_callback, parent=None, show_loading_callback=None):
    if not check_docker_running(): return
    confirm_and_run("Delete ALL containers?", DOCKER_RM_ALL,
                   show_text_output_callback, sudo=True, parent=parent,
                   show_loading_callback=show_loading_callback)
