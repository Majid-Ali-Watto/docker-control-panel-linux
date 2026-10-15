"""
Stats dialogs: docker disk usage view.
"""

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import async_run, parse_fixed_width_table
from src.docker.commands import DOCKER_DISK_USAGE_VERBOSE

# (tab label, heading `docker system df -v` prints above the section, table type)
_SECTIONS = (
    ("Images", "Images space usage", "disk_images"),
    ("Containers", "Containers space usage", "disk_containers"),
    ("Volumes", "Local Volumes space usage", "disk_volumes"),
    ("Build Cache", "Build cache usage", "disk_cache"),
)

# Tab the user was last looking at, so reloading the view (e.g. after deleting a row) stays on it
_active_tab = {"label": _SECTIONS[0][0]}


def _parse_sections(result):
    """Split `docker system df -v` output into {tab label: (columns, rows)}."""
    sections = {}
    lines = result.splitlines()
    i = 0
    while i < len(lines):
        section = next((s for s in _SECTIONS if lines[i].startswith(s[1])), None)
        if section and i + 2 < len(lines):
            header = lines[i + 2]
            data = []
            i += 3
            while i < len(lines) and lines[i].strip():
                data.append(lines[i])
                i += 1
            sections[section[0]] = parse_fixed_width_table(data, header)
        i += 1
    return sections


def docker_disk_usage_view(display_manager, loading_callback):
    """Show Docker disk usage: one table per section (images, containers, volumes, build cache),
    switched with a tab strip, each with the usual search, sort and row actions."""
    if not check_docker_running(): return

    def callback(result):
        sections = _parse_sections(result)
        if not sections:
            display_manager.show_text_output(f"Docker Disk Usage\n\n{result}".strip())
            return

        def show(label):
            _active_tab["label"] = label
            columns, rows = sections[label]
            table_type = next(s[2] for s in _SECTIONS if s[0] == label)
            display_manager.show_table(
                columns, rows, table_type, f"Docker Disk Usage — {label}",
                tabs={name: (lambda name=name: show(name)) for name in sections}, active_tab=label)

        show(_active_tab["label"] if _active_tab["label"] in sections else next(iter(sections)))

    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=True, sudo_password=get_sudo_password(),
              loading_callback=loading_callback)
