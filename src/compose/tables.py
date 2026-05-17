"""
Compose project table views.
"""

import json

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import async_run
from src.docker.commands import DOCKER_COMPOSE_LS


def show_compose_projects(show_table_callback, show_loading_callback):
    """Show Docker Compose projects"""
    if not check_docker_running(): return

    def callback(result):
        rows = []
        try:
            data = json.loads(result.strip() or "[]")
            for item in data:
                rows.append([
                    item.get("Name", ""),
                    item.get("Status", ""),
                    item.get("ConfigFiles", ""),
                ])
        except (json.JSONDecodeError, TypeError):
            pass

        show_table_callback(
            ["PROJECT", "STATUS", "CONFIG FILES"],
            rows,
            'compose',
            "Compose Projects",
            False
        )

    async_run(
        DOCKER_COMPOSE_LS,
        callback, sudo=True, sudo_password=get_sudo_password(), loading_callback=show_loading_callback
    )
