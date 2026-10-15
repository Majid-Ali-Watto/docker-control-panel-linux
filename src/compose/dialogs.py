"""
Compose dialogs: compose up from files or a project folder.
"""

import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password, load_compose_projects, save_compose_project
from src.docker.operations import run_docker_cmd
from src.docker.commands import DOCKER_COMPOSE_UP, DOCKER_COMPOSE_UP_BUILD
from src.shared.helpers import _join_flag_values, _center_dialog, _ERROR_HINTS
from src.utils.threads import startThreadForTask
from src.utils.utils import run_cmd


def _parse_conflict_container_ids(output):
    """Return list of container IDs that caused 'name already in use' conflicts."""
    return re.findall(
        r'container name .+ already in use by container "([a-f0-9]+)"',
        output,
        re.IGNORECASE,
    )


# Default file names docker compose looks for in a project folder (in its order of precedence)
_COMPOSE_FILE_NAMES = ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml")


def _compose_files_in_folder(folder):
    """The compose file docker would pick in a folder, plus the override file it merges with it."""
    for name in _COMPOSE_FILE_NAMES:
        base = os.path.join(folder, name)
        if os.path.isfile(base):
            stem = os.path.splitext(base)[0]
            overrides = [p for p in (f"{stem}.override.yaml", f"{stem}.override.yml") if os.path.isfile(p)]
            return [base] + overrides[:1]
    return []


def _last_project_dir():
    projects = load_compose_projects()
    return os.path.dirname(projects[-1][0]) if projects else None


def _ask_compose_files(root):
    """Let the user pick compose files or a project folder and whether to rebuild images.

    Returns (paths, build) or None when cancelled.
    """
    start_dir = _last_project_dir()
    chosen = []
    build_var = tk.BooleanVar(master=root, value=False)

    dialog = tk.Toplevel(root)
    dialog.title("Compose Up")
    dialog.transient(root)
    dialog.grab_set()

    def pick_files():
        files = filedialog.askopenfilenames(
            parent=dialog, title="Select Compose File(s)", initialdir=start_dir,
            filetypes=[("Compose files", "*.yml *.yaml"), ("All files", "*.*")])
        if files:
            chosen.extend(files)
            dialog.destroy()

    def pick_folder():
        folder = filedialog.askdirectory(parent=dialog, title="Select Project Folder",
                                         initialdir=start_dir, mustexist=True)
        if not folder:
            return
        files = _compose_files_in_folder(folder)
        if not files:
            messagebox.showerror(
                "No Compose File Found",
                f"No compose file in:\n{folder}\n\nExpected one of: {', '.join(_COMPOSE_FILE_NAMES)}",
                parent=dialog)
            return
        chosen.extend(files)
        dialog.destroy()

    ttk.Label(dialog, text="Start a compose project from:", font=("Arial", 10)).pack(padx=20, pady=(20, 8))
    ttk.Checkbutton(dialog, text="Rebuild images first (--build)", variable=build_var).pack(padx=20, anchor="w")
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(padx=20, pady=(4, 20))
    ttk.Button(btn_frame, text="Compose File(s)…", style="primary.TButton",
               command=pick_files, width=18).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Project Folder…", style="primary.TButton",
               command=pick_folder, width=18).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
    dialog.bind("<Escape>", lambda e: dialog.destroy())
    _center_dialog(dialog, min_width=460)
    dialog.wait_window()
    return (chosen, build_var.get()) if chosen else None


def compose_up_from_file_dialog(root, show_text_output_callback, refresh_callback=None, show_loading_callback=None):
    """Start a compose project from selected compose file(s) or a project folder."""
    if not check_docker_running(): return

    selection = _ask_compose_files(root)
    if not selection:
        return
    files, build = selection

    # Validate: at least one file must contain a 'services:' key
    try:
        contents = []
        for path in files:
            with open(path, 'r') as fh:
                contents.append(fh.read())
        if not any('services:' in content for content in contents):
            messagebox.showerror(
                "Invalid Compose File",
                f"The selected file does not appear to be a valid Docker Compose file "
                f"(no 'services:' key found).\n\n"
                f"File: {files[0]}\n\n"
                f"Tip: look for a file named docker-compose.yml that contains a 'services:' section.",
                parent=root,
            )
            return
    except OSError as exc:
        messagebox.showerror("Cannot Read File", str(exc), parent=root)
        return

    # Remembered so the project stays in the Projects list (and can be started again) after `down`
    save_compose_project(files)

    def _run_compose_up():
        files_arg = _join_flag_values('-f', files).strip()
        command = (DOCKER_COMPOSE_UP_BUILD if build else DOCKER_COMPOSE_UP).format(files=files_arg)
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
