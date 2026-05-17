"""
Network table views.
"""

from src.docker.operations import show_table_command
from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.docker.commands import DOCKER_NETWORK_LS


def show_networks(show_table_callback, show_loading_callback):
    """Show Docker networks"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_NETWORK_LS,
        ["NETWORK ID", "NAME", "DRIVER", "SCOPE"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='network',
        table_title="Docker Networks"
    )
