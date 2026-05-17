"""
Network bulk actions (prune).
"""

from src.docker.actions import check_docker_running, confirm_and_run
from src.docker.commands import DOCKER_NETWORK_PRUNE


def prune_networks(show_text_output_callback, parent=None, show_loading_callback=None):
    """Delete unused Docker networks"""
    if not check_docker_running(): return
    confirm_and_run("Delete unused Docker networks?", DOCKER_NETWORK_PRUNE,
                   show_text_output_callback, sudo=True, parent=parent,
                   show_loading_callback=show_loading_callback)
