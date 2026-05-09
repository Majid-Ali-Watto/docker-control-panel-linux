"""
Docker Tables Module
Functions to display Docker resources in tables.
"""

import tkinter as tk
from tkinter import ttk
from src.docker.docker_operations import show_table_command
from src.docker.docker_actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import async_run, run_cmd
from src.docker.docker_commands_constants import (
    DOCKER_PS_RUNNING,
    DOCKER_PS_ALL,
    DOCKER_PS_STOPPED,
    DOCKER_PS_PAUSED,
    DOCKER_PS_IDS_RUNNING,
    DOCKER_STATS_NO_STREAM,
    DOCKER_IMAGES_ALL,
    DOCKER_PS_IDS_ALL,
    DOCKER_INSPECT_IMAGE,
    DOCKER_PS_NAMES_ALL,
    DOCKER_INSPECT_MOUNTS,
    DOCKER_DISK_USAGE_VERBOSE,
    DOCKER_DISK_STORAGE_SIMPLE,
    DOCKER_NETWORK_LS,
    DOCKER_COMPOSE_LS,
)


def show_running_containers(show_table_callback, show_loading_callback, append=False):
    """Show running containers"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_PS_RUNNING,
        ["CONTAINER ID", "NAMES", "IMAGE", "STATUS", "PORTS", "SIZE"],
        sudo=False,
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
        sudo=False,
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
        sudo=False,
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
        sudo=False,
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='container',
        table_title="Paused Containers",
        append=append
    )


def show_containers_with_stats(show_table_callback, show_loading_callback, display_manager=None):
    """Show containers with stats (only running containers for better performance)"""
    if not check_docker_running(): return
    
    # Add refresh button immediately if display_manager is provided
    if display_manager:
        import tkinter as tk
        from tkinter import ttk
        
        refresh_btn = None
        live_btn = None
        for widget in display_manager.action_frame.winfo_children():
            if isinstance(widget, ttk.Button) and "Refresh" in str(widget.cget("text")):
                refresh_btn = widget
            if isinstance(widget, ttk.Button) and "Live Stats" in str(widget.cget("text")):
                live_btn = widget
        
        def refresh_stats():
            show_containers_with_stats(show_table_callback, show_loading_callback, display_manager)

        def toggle_live_stats():
            display_manager.live_stats_enabled = not display_manager.live_stats_enabled
            if not display_manager.live_stats_enabled:
                display_manager.stop_live_stats()
            refresh_stats()

        if not refresh_btn:
            refresh_btn = ttk.Button(display_manager.action_frame, text="🔄 Refresh Stats")
            refresh_btn.config(command=refresh_stats)

        if not live_btn:
            live_btn = ttk.Button(display_manager.action_frame, text="▶ Live Stats")
            live_btn.config(command=toggle_live_stats)

        live_btn.config(text="⏹ Stop Live Stats" if display_manager.live_stats_enabled else "▶ Live Stats")
    
    # First check if there are running containers
    running = run_cmd(DOCKER_PS_IDS_RUNNING).strip()
    if not running:
        # No running containers
        show_table_callback(
            ["CONTAINER ID", "NAME", "CPU %", "MEM USAGE", "MEM %", "NET I/O", "BLOCK I/O", "PIDs"],
            [], 'container_stats', "Container Stats", False
        )
        if display_manager and display_manager.live_stats_enabled:
            display_manager.live_stats_job = display_manager.output_container.after(
                2000,
                lambda: show_containers_with_stats(show_table_callback, show_loading_callback, display_manager)
            )
        return
    
    def callback(result):
        # Parse docker stats output
        rows = []
        for line in result.split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 7:  # Ensure all columns are present
                    rows.append(parts)
        
        if not rows:
            rows = []  # Empty if no stats collected
            
        show_table_callback(
            ["CONTAINER ID", "NAME", "CPU %", "MEM USAGE", "MEM %", "NET I/O", "BLOCK I/O", "PIDs"],
            rows, 'container_stats', "Container Stats (Running Containers Only)", False
        )

        if display_manager and display_manager.live_stats_enabled:
            if display_manager.live_stats_job:
                try:
                    display_manager.output_container.after_cancel(display_manager.live_stats_job)
                except Exception:
                    pass
            display_manager.live_stats_job = display_manager.output_container.after(
                2000,
                lambda: show_containers_with_stats(show_table_callback, show_loading_callback, display_manager)
            )
    
    # Only query running containers for faster performance
    async_run(
        DOCKER_STATS_NO_STREAM,
        callback, sudo=False, sudo_password=None, loading_callback=show_loading_callback
    )


def show_images(show_table_callback, show_loading_callback):
    """Show all images"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_IMAGES_ALL,
        ["REPOSITORY", "TAG", "IMAGE ID", "SIZE"],
        sudo=False,
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='image',
        table_title="Images"
    )


def show_unused_images(show_table_callback, show_loading_callback, append=False):
    """Show unused images"""
    if not check_docker_running(): return
    
    def callback(result):
        # Get all images
        all_image_rows = []
        for line in result.split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4:
                    all_image_rows.append(parts)
        
        # Get images used by containers
        container_ids = run_cmd(DOCKER_PS_IDS_ALL).strip()
        used_image_ids = set()
        
        if container_ids:
            for container_id in container_ids.split('\n'):
                if container_id.strip():
                    image_sha = run_cmd(f"docker inspect --format='{{{{.Image}}}}' {container_id.strip()}").strip()
                    if image_sha:
                        image_sha = image_sha.replace('sha256:', '')
                        used_image_ids.add(image_sha)
                        used_image_ids.add(image_sha[:12])
        
        # Filter unused images
        unused_rows = [row for row in all_image_rows if row[2] not in used_image_ids]
        show_table_callback(["REPOSITORY", "TAG", "IMAGE ID", "SIZE"], unused_rows, 
                          'image', "Unused Images", append)
    
    async_run(
        DOCKER_IMAGES_ALL,
        callback, sudo=False, sudo_password=None, loading_callback=show_loading_callback
    )


def show_used_images(show_table_callback, show_loading_callback, append=False):
    """Show used images"""
    if not check_docker_running(): return
    
    def callback(result):
        # Get all images
        all_image_rows = []
        for line in result.split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 4:
                    all_image_rows.append(parts)
        
        # Get images used by containers
        container_ids = run_cmd(DOCKER_PS_IDS_ALL).strip()
        used_image_ids = set()
        
        if container_ids:
            for container_id in container_ids.split('\n'):
                if container_id.strip():
                    image_sha = run_cmd(DOCKER_INSPECT_IMAGE.format(container_id=container_id.strip())).strip()
                    if image_sha:
                        image_sha = image_sha.replace('sha256:', '')
                        used_image_ids.add(image_sha)
                        used_image_ids.add(image_sha[:12])
        
        # Filter used images
        used_rows = [row for row in all_image_rows if row[2] in used_image_ids]
        show_table_callback(["REPOSITORY", "TAG", "IMAGE ID", "SIZE"], used_rows, 
                          'image', "Used Images", append)
    
    async_run(
        DOCKER_IMAGES_ALL,
        callback, sudo=False, sudo_password=None, loading_callback=show_loading_callback
    )


def _collect_volume_rows(result):
    """Collect volume rows with usage details from docker system df -v output."""
    volume_containers = {}

    containers_result = run_cmd(DOCKER_PS_NAMES_ALL).strip()
    if containers_result:
        container_names = containers_result.split('\n')
        for container_name in container_names:
            if container_name.strip():
                mounts = run_cmd(DOCKER_INSPECT_MOUNTS.format(container_name=container_name)).strip()
                if mounts and mounts != '[]':
                    import json
                    try:
                        mount_list = json.loads(mounts)
                        for mount in mount_list:
                            if mount.get('Type') == 'volume':
                                vol_name = mount.get('Name')
                                if vol_name:
                                    if vol_name not in volume_containers:
                                        volume_containers[vol_name] = []
                                    volume_containers[vol_name].append(container_name)
                    except Exception:
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
    
    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=False, sudo_password=None, 
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

    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=False, sudo_password=None,
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

    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=False, sudo_password=None,
             loading_callback=show_loading_callback)


def show_docker_disk_storage_simple(show_table_callback, show_loading_callback):
    """Show Docker disk storage summary in simple table format"""
    if not check_docker_running(): return
    
    def callback(result):
        # Parse docker system df output
        import re
        lines = result.split('\n')
        rows = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('TYPE'):
                continue
            
            # Split by 2 or more spaces to properly separate columns
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 5:
                type_name = parts[0]
                total = parts[1]
                active = parts[2]
                size = parts[3]
                reclaimable = parts[4]
                
                rows.append([type_name, total, active, size, reclaimable])
        
        show_table_callback(
            ["TYPE", "TOTAL", "ACTIVE", "SIZE", "RECLAIMABLE"],
            rows, 'disk_storage', "Docker Disk Storage", False
        )
    
    async_run(DOCKER_DISK_STORAGE_SIMPLE, callback, sudo=False, sudo_password=None, 
             loading_callback=show_loading_callback)


def show_networks(show_table_callback, show_loading_callback):
    """Show Docker networks"""
    if not check_docker_running(): return
    show_table_command(
        DOCKER_NETWORK_LS,
        ["NETWORK ID", "NAME", "DRIVER", "SCOPE"],
        sudo=False,
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='network',
        table_title="Docker Networks"
    )


def show_compose_projects(show_table_callback, show_loading_callback):
    """Show Docker Compose projects"""
    if not check_docker_running(): return

    def callback(result):
        import json
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
        callback, sudo=False, sudo_password=None, loading_callback=show_loading_callback
    )
