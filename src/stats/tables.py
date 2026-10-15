"""
Stats table views: container stats and disk storage summary.
"""

import re
import tkinter as tk
from collections import deque
from tkinter import ttk

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password, get_setting, set_setting
from src.utils.utils import async_run, run_cmd
from src.docker.commands import (
    DOCKER_STATS_NO_STREAM,
    DOCKER_DISK_STORAGE_SIMPLE,
    DOCKER_PS_IDS_RUNNING,
)


_COLUMNS = ["CONTAINER ID", "NAME", "CPU %", "MEM USAGE", "MEM %", "NET I/O", "BLOCK I/O", "PIDs",
            "CPU TREND", "MEM TREND"]
_INTERVALS = (1, 2, 3, 5, 10)      # seconds between Live Stats refreshes, cycled by the ⏱ button
_BARS = "▁▂▃▄▅▆▇█"
_HISTORY_LEN = 20
_history = {}                      # container id -> {"cpu": deque, "mem": deque} of recent samples


def sparkline(values, top=None):
    """The samples as block characters, scaled from 0 to `top` (default: the largest sample, at
    least 1 so an idle container shows a flat line)."""
    if not values:
        return ""
    top = top or max(max(values), 1.0)
    return "".join(_BARS[min(len(_BARS) - 1, int(max(v, 0) / top * (len(_BARS) - 1) + 0.5))] for v in values)


def _percent(text):
    try:
        return float(str(text).strip().rstrip("%"))
    except ValueError:
        return None


def _with_trends(rows):
    """Rows extended with CPU / MEM trend columns built from the samples of the last refreshes;
    history of containers that are gone is dropped."""
    for gone in set(_history) - {row[0] for row in rows}:
        del _history[gone]
    result = []
    for row in rows:
        series = _history.setdefault(row[0], {"cpu": deque(maxlen=_HISTORY_LEN), "mem": deque(maxlen=_HISTORY_LEN)})
        for key, index in (("cpu", 2), ("mem", 4)):
            value = _percent(row[index]) if len(row) > index else None
            if value is not None:
                series[key].append(value)
        result.append(list(row) + [sparkline(series["cpu"]), sparkline(series["mem"], top=100)])
    return result


def _interval_ms():
    return int(get_setting("stats_interval")) * 1000


def show_containers_with_stats(show_table_callback, show_loading_callback, display_manager=None):
    """Show containers with stats (only running containers for better performance)"""
    if not check_docker_running(): return

    if display_manager:
        refresh_btn = None
        live_btn = None
        interval_btn = None
        for widget in display_manager.action_frame.winfo_children():
            if isinstance(widget, ttk.Button) and "Refresh" in str(widget.cget("text")):
                refresh_btn = widget
            if isinstance(widget, ttk.Button) and "Live Stats" in str(widget.cget("text")):
                live_btn = widget
            if isinstance(widget, ttk.Button) and "⏱" in str(widget.cget("text")):
                interval_btn = widget

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

        def cycle_interval():
            current = int(get_setting("stats_interval"))
            following = next((n for n in _INTERVALS if n > current), _INTERVALS[0])
            set_setting("stats_interval", following)
            interval_btn.config(text=f"⏱ {following}s")

        if not live_btn:
            live_btn = ttk.Button(display_manager.action_frame, text="▶ Live Stats")
            live_btn.config(command=toggle_live_stats)

        if not interval_btn:
            interval_btn = ttk.Button(display_manager.action_frame, style="secondary.TButton")
            interval_btn.config(command=cycle_interval)
        interval_btn.config(text=f"⏱ {int(get_setting('stats_interval'))}s")

        live_btn.config(text="⏹ Stop Live Stats" if display_manager.live_stats_enabled else "▶ Live Stats")

    running = run_cmd(DOCKER_PS_IDS_RUNNING, sudo=True, sudo_password=get_sudo_password()).strip()
    if not running:
        show_table_callback(
            _COLUMNS, [], 'container_stats', "Container Stats (Running Containers Only)", False
        )
        if display_manager and display_manager.live_stats_enabled:
            display_manager.live_stats_job = display_manager.output_container.after(
                _interval_ms(),
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
            _COLUMNS, _with_trends(rows), 'container_stats', "Container Stats (Running Containers Only)", False
        )

        if display_manager and display_manager.live_stats_enabled:
            if display_manager.live_stats_job:
                try:
                    display_manager.output_container.after_cancel(display_manager.live_stats_job)
                except Exception:
                    pass
            display_manager.live_stats_job = display_manager.output_container.after(
                _interval_ms(),
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
