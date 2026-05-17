"""
Stats table views: container stats and disk storage summary.
"""

import re
import tkinter as tk
from tkinter import ttk

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import async_run, run_cmd
from src.docker.commands import (
    DOCKER_STATS_NO_STREAM,
    DOCKER_DISK_STORAGE_SIMPLE,
    DOCKER_PS_IDS_RUNNING,
)


def show_containers_with_stats(show_table_callback, show_loading_callback, display_manager=None):
    """Show containers with stats (only running containers for better performance)"""
    if not check_docker_running(): return

    if display_manager:
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

    running = run_cmd(DOCKER_PS_IDS_RUNNING, sudo=True, sudo_password=get_sudo_password()).strip()
    if not running:
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
        rows = []
        for line in result.split('\n'):
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 7:
                    rows.append(parts)

        if not rows:
            rows = []

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

    async_run(
        DOCKER_STATS_NO_STREAM,
        callback, sudo=True, sudo_password=get_sudo_password(), loading_callback=show_loading_callback
    )


def show_docker_disk_storage_simple(show_table_callback, show_loading_callback):
    """Show Docker disk storage summary in simple table format"""
    if not check_docker_running(): return

    def callback(result):
        lines = result.split('\n')
        rows = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('TYPE'):
                continue

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

    async_run(DOCKER_DISK_STORAGE_SIMPLE, callback, sudo=True, sudo_password=get_sudo_password(),
             loading_callback=show_loading_callback)
