"""
Volume dialogs: create volume.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.docker.operations import run_docker_cmd
from src.docker.commands import DOCKER_VOLUME_CREATE
from src.shared.helpers import _quote, _center_dialog, _make_output_callback


def create_volume_dialog(root, show_text_output_callback, refresh_callback=None):
    """Create a new Docker volume."""
    if not check_docker_running(): return

    dialog = tk.Toplevel(root)
    dialog.title("Create Docker Volume")
    dialog.transient(root)
    dialog.grab_set()

    ttk.Label(dialog, text="Volume name:", font=("Arial", 10)).pack(padx=20, pady=(20, 8), anchor="w")
    name_var = tk.StringVar()
    entry = ttk.Entry(dialog, textvariable=name_var, width=36)
    entry.pack(padx=20, pady=4)
    entry.focus()

    def on_create():
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("Name Required", "Please enter a volume name.", parent=dialog)
            return
        dialog.destroy()
        run_docker_cmd(
            DOCKER_VOLUME_CREATE.format(name=_quote(name)),
            sudo=True,
            sudo_password=get_sudo_password(),
            callback=_make_output_callback(show_text_output_callback, "Volume Create", refresh_callback, root),
        )

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(10, 20))
    ttk.Button(btn_frame, text="Create", style="primary.TButton", command=on_create, width=12).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    entry.bind("<Return>", lambda e: on_create())
    entry.bind("<Escape>", lambda e: dialog.destroy())
    _center_dialog(dialog, min_width=360)
