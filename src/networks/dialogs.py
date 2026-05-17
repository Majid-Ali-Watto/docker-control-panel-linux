"""
Network dialogs: create network.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.docker.operations import run_docker_cmd
from src.docker.commands import DOCKER_NETWORK_CREATE
from src.shared.helpers import _quote, _center_dialog, _make_output_callback


def create_network_dialog(root, show_text_output_callback, refresh_callback=None):
    """Create a new Docker network."""
    if not check_docker_running(): return

    dialog = tk.Toplevel(root)
    dialog.title("Create Docker Network")
    dialog.transient(root)
    dialog.grab_set()

    ttk.Label(dialog, text="Network name:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))
    name_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=name_var, width=36).grid(row=0, column=1, sticky="ew", padx=16, pady=(16, 6))

    ttk.Label(dialog, text="Driver:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=16, pady=6)
    driver_var = tk.StringVar(value="bridge")
    ttk.Combobox(dialog, textvariable=driver_var, values=["bridge", "overlay", "host", "macvlan"], state="readonly", width=20).grid(row=1, column=1, sticky="w", padx=16, pady=6)

    ttk.Label(dialog, text="Subnet (optional):", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=16, pady=6)
    subnet_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=subnet_var, width=36).grid(row=2, column=1, sticky="ew", padx=16, pady=6)

    ttk.Label(dialog, text="Gateway (optional):", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=16, pady=6)
    gateway_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=gateway_var, width=36).grid(row=3, column=1, sticky="ew", padx=16, pady=6)

    dialog.columnconfigure(1, weight=1)

    def on_create():
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("Name Required", "Please enter a network name.", parent=dialog)
            return

        options = ""
        if subnet_var.get().strip():
            options += f" --subnet {_quote(subnet_var.get().strip())}"
        if gateway_var.get().strip():
            options += f" --gateway {_quote(gateway_var.get().strip())}"

        dialog.destroy()
        run_docker_cmd(
            DOCKER_NETWORK_CREATE.format(
                driver=_quote(driver_var.get().strip() or "bridge"),
                options=options,
                name=_quote(name),
            ),
            sudo=True,
            sudo_password=get_sudo_password(),
            callback=_make_output_callback(show_text_output_callback, "Network Create", refresh_callback, root),
        )

    btn_frame = ttk.Frame(dialog)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=(10, 16))
    ttk.Button(btn_frame, text="Create", style="primary.TButton", command=on_create, width=12).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    _center_dialog(dialog, min_width=520)
