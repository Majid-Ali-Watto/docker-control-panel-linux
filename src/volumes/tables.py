"""
Volume table views.
"""

import json

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import async_run, run_cmd
from src.docker.commands import (
    DOCKER_DISK_USAGE_VERBOSE,
    DOCKER_PS_NAMES_ALL,
    DOCKER_INSPECT_MOUNTS,
)


def _collect_volume_rows(result):
    """Collect volume rows with usage details from docker system df -v output."""
    volume_containers = {}

    sudo_pw = get_sudo_password()
    containers_result = run_cmd(DOCKER_PS_NAMES_ALL, sudo=True, sudo_password=sudo_pw).strip()
    if containers_result:
        container_names = containers_result.split('\n')
        for container_name in container_names:
            if container_name.strip():
                mounts = run_cmd(DOCKER_INSPECT_MOUNTS.format(container_name=container_name), sudo=True, sudo_password=sudo_pw).strip()
                if mounts and mounts != '[]':
                    try:
                        mount_list = json.loads(mounts)
                        for mount in mount_list:
                            if mount.get('Type') == 'volume':
                                vol_name = mount.get('Name')
                                if vol_name:
                                    if vol_name not in volume_containers:
                                        volume_containers[vol_name] = []
                                    volume_containers[vol_name].append(container_name)
                    except (json.JSONDecodeError, ValueError):
                        pass

    lines = result.split('\n')
    in_volumes = False
    rows = []
    for line in lines:
        if 'Local Volumes space usage:' in line or 'VOLUME NAME' in line:
            in_volumes = True
            continue
        if in_volumes and line.strip() and not line.startswith('Images'):
            parts = line.split()
            if len(parts) >= 3 and not line.startswith('VOLUME') and not line.startswith('Container'):
                volume_name = parts[0]
                links = parts[1] if len(parts) > 1 else '0'
                size = parts[2] if len(parts) > 2 else '0B'

                containers = volume_containers.get(volume_name, [])
                used_by = ', '.join(containers) if containers else '(unused)'

                rows.append([volume_name, links, size, used_by])
        if in_volumes and ('Images space usage:' in line or 'Containers space usage:' in line or 'Build' in line):
            break

    return rows


def show_volumes(show_table_callback, show_loading_callback):
    """Show volumes with container usage information"""
    if not check_docker_running(): return

    def callback(result):
        rows = _collect_volume_rows(result)
        show_table_callback(["VOLUME NAME", "LINKS", "SIZE", "USED BY"], rows, 'volume', "Volumes", False)

    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=True, sudo_password=get_sudo_password(),
             loading_callback=show_loading_callback)


def show_used_volumes(show_table_callback, show_loading_callback, append=False):
    """Show used volumes only."""
    if not check_docker_running(): return

    def callback(result):
        rows = [row for row in _collect_volume_rows(result) if row[3] != '(unused)']
        show_table_callback(
            ["VOLUME NAME", "LINKS", "SIZE", "USED BY"],
            rows,
            'volume',
            "Used Volumes",
            append
        )

    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=True, sudo_password=get_sudo_password(),
             loading_callback=show_loading_callback)


def show_unused_volumes(show_table_callback, show_loading_callback, append=False):
    """Show unused volumes only."""
    if not check_docker_running(): return

    def callback(result):
        rows = [row for row in _collect_volume_rows(result) if row[3] == '(unused)']
        show_table_callback(
            ["VOLUME NAME", "LINKS", "SIZE", "USED BY"],
            rows,
            'volume',
            "Unused Volumes",
            append
        )

    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=True, sudo_password=get_sudo_password(),
             loading_callback=show_loading_callback)
