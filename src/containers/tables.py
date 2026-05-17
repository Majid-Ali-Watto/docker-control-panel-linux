"""
Container table views.
"""

from src.docker.operations import show_table_command
from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.docker.commands import (
    DOCKER_PS_RUNNING,
    DOCKER_PS_ALL,
    DOCKER_PS_STOPPED,
    DOCKER_PS_PAUSED,
)


def show_running_containers(show_table_callback, show_loading_callback, append=False):
    """Show running containers"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_PS_RUNNING,
        ["CONTAINER ID", "NAMES", "IMAGE", "STATUS", "PORTS", "SIZE"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='container',
        table_title="Running Containers",
        append=append
    )


def show_all_containers(show_table_callback, show_loading_callback):
    """Show all containers"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_PS_ALL,
        ["CONTAINER ID", "NAMES", "IMAGE", "STATUS", "PORTS", "SIZE"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='container',
        table_title="All Containers"
    )


def show_stopped_containers(show_table_callback, show_loading_callback, append=False):
    """Show stopped containers"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_PS_STOPPED,
        ["CONTAINER ID", "NAMES", "IMAGE", "STATUS", "PORTS", "SIZE"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='container',
        table_title="Stopped Containers",
        append=append
    )


def show_paused_containers(show_table_callback, show_loading_callback, append=False):
    """Show paused containers"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_PS_PAUSED,
        ["CONTAINER ID", "NAMES", "IMAGE", "STATUS", "PORTS", "SIZE"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='container',
        table_title="Paused Containers",
        append=append
    )
