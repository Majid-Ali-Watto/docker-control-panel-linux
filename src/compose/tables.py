"""
Compose project table views.
"""

import json
import os
import re

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password, load_compose_projects
from src.utils.utils import async_run
from src.docker.commands import DOCKER_COMPOSE_LS


def _saved_project_rows(listed_files):
    """Rows for remembered projects docker no longer lists (e.g. after `compose down`).

    Projects whose files have gone missing are hidden, not forgotten (the drive may be unmounted).
    """
    rows = []
    for files in load_compose_projects():
        if frozenset(files) in listed_files or not all(os.path.exists(f) for f in files):
            continue
        # compose names a project after its directory unless the file sets `name:`
        name = re.sub(r"[^a-z0-9_-]", "", os.path.basename(os.path.dirname(files[0])).lower())
        rows.append([name or "project", "not running", ",".join(files)])
    return rows


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
        listed = {frozenset(f.strip() for f in row[2].split(",")) for row in rows}
        rows += _saved_project_rows(listed)

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
