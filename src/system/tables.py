"""
System table views: Docker contexts.
"""

from src.docker.operations import show_table_command
from src.config.config_manager import get_sudo_password
from src.docker.commands import DOCKER_CONTEXT_LS


def show_contexts(show_table_callback, show_loading_callback):
    """List contexts (local and remote engines). No daemon check: a remote context works while the
    local Docker service is stopped."""
    show_table_command(
        DOCKER_CONTEXT_LS,
        ["NAME", "DESCRIPTION", "DOCKER ENDPOINT", "CURRENT"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='context',
        table_title="Docker Contexts",
    )
