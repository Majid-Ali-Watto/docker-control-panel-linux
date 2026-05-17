"""
Compose dialogs: compose up from file.
"""

import re
import tkinter as tk
from tkinter import messagebox, filedialog

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.docker.operations import run_docker_cmd
from src.docker.commands import DOCKER_COMPOSE_UP
from src.shared.helpers import _compose_files_to_args, _ERROR_HINTS
from src.utils.threads import startThreadForTask
from src.utils.utils import run_cmd


def _parse_conflict_container_ids(output):
    """Return list of container IDs that caused 'name already in use' conflicts."""
    return re.findall(
        r'container name .+ already in use by container "([a-f0-9]+)"',
        output,
        re.IGNORECASE,
    )


def compose_up_from_file_dialog(root, show_text_output_callback, refresh_callback=None, show_loading_callback=None):
    """Start a compose project from a selected compose file."""
    if not check_docker_running(): return

    filename = filedialog.askopenfilename(
        parent=root,
        title="Select Compose File",
        filetypes=[
            ("Compose files", "*.yml *.yaml"),
            ("All files", "*.*"),
        ],
    )
    if not filename:
        return

    # Validate: file must contain a 'services:' key
    try:
        with open(filename, 'r') as fh:
            content = fh.read()
        if 'services:' not in content:
            messagebox.showerror(
                "Invalid Compose File",
                f"The selected file does not appear to be a valid Docker Compose file "
                f"(no 'services:' key found).\n\n"
                f"File: {filename}\n\n"
                f"Tip: look for a file named docker-compose.yml that contains a 'services:' section.",
                parent=root,
            )
            return
    except OSError as exc:
        messagebox.showerror("Cannot Read File", str(exc), parent=root)
        return

    def _run_compose_up():
        files_arg = _compose_files_to_args(filename)
        command = DOCKER_COMPOSE_UP.format(files=files_arg)
        run_docker_cmd(
            command,
            sudo=True,
            sudo_password=get_sudo_password(),
            callback=_on_compose_up_result,
            loading_callback=show_loading_callback,
        )

    def _on_compose_up_result(result):
        show_text_output_callback(f"Compose Up\n\n{result}".strip())

        conflict_ids = _parse_conflict_container_ids(result)
        if conflict_ids:
            names = re.findall(r'container name "(/[^"]+)" is already in use', result, re.IGNORECASE)
            name_list = "\n".join(f"  • {n}" for n in names) if names else \
                        "\n".join(f"  • {cid[:12]}" for cid in conflict_ids)
            answer = messagebox.askyesno(
                "Container Conflicts — Remove and Retry?",
                f"The following containers are blocking the compose project:\n\n"
                f"{name_list}\n\n"
                f"Remove them now and retry Compose Up?",
                icon="warning",
                parent=root,
            )
            if answer:
                _remove_and_retry(conflict_ids)
            return

        result_lower = result.lower()
        has_error = any(hint in result_lower for hint in _ERROR_HINTS)
        if not has_error and refresh_callback and root:
            root.after(800, refresh_callback)

    def _remove_and_retry(container_ids):
        def task():
            if show_loading_callback:
                show_loading_callback(True)
            ids_str = " ".join(container_ids)
            remove_result = run_cmd(
                f"docker rm -f {ids_str}",
                sudo=True,
                sudo_password=get_sudo_password(),
            )
            if show_loading_callback:
                show_loading_callback(False)
            show_text_output_callback(f"Removed conflicting containers:\n{remove_result}\n\nRetrying Compose Up…")
            root.after(300, _run_compose_up)

        startThreadForTask(task)

    _run_compose_up()
