"""
Settings dialog: the few preferences stored in ~/.docker-gui/config.json (see
config_manager.DEFAULT_SETTINGS).
"""

import shutil
import tkinter as tk
from tkinter import ttk, messagebox

from src.config.config_manager import get_setting, set_setting, password_storage
from src.shared.helpers import _center_dialog
from src.stats.tables import _INTERVALS
from src.ui.rounded import readable_color
from src.utils.utils import installed_terminals, docker_needs_sudo

_ENGINES = ("docker", "podman")


def settings_dialog(root):
    """Edit the preferences; they apply as soon as they are saved (the engine from the next command)."""
    dialog = tk.Toplevel(root)
    dialog.title("Settings")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    form = ttk.Frame(dialog)
    form.pack(padx=20, pady=(18, 6), fill=tk.X)
    form.columnconfigure(1, weight=1)

    interval_var = tk.StringVar(value=f"{int(get_setting('stats_interval'))}s")
    engine_var = tk.StringVar(value=get_setting("engine"))
    notify_var = tk.BooleanVar(value=get_setting("notifications"))
    terminal_var = tk.StringVar(value=get_setting("terminal"))

    def row(index, label, widget, hint=None):
        ttk.Label(form, text=label, font=("Arial", 10)).grid(row=index * 2, column=0, sticky="w", pady=(8, 0))
        widget.grid(row=index * 2, column=1, sticky="ew", padx=(12, 0), pady=(8, 0))
        if hint:
            ttk.Label(form, text=hint, font=("Arial", 8), foreground=readable_color("gray"), wraplength=330,
                      justify=tk.LEFT).grid(row=index * 2 + 1, column=1, sticky="w", padx=(12, 0))

    row(0, "Live Stats refresh:",
        ttk.Combobox(form, textvariable=interval_var, state="readonly", width=24,
                     values=[f"{n}s" for n in _INTERVALS]),
        "How often Stats → Container Stats reloads while Live Stats is on.")
    row(1, "Container engine:",
        ttk.Combobox(form, textvariable=engine_var, state="readonly", width=24, values=_ENGINES),
        "Podman is experimental: the Docker service buttons and status still refer to Docker. "
        "Relaunch the app after changing it.")
    row(2, "Terminal:",
        ttk.Combobox(form, textvariable=terminal_var, state="readonly", width=24,
                     values=["auto"] + installed_terminals()),
        "Emulator used by the Container Terminal action (auto: first one installed).")

    notify_check = ttk.Checkbutton(form, variable=notify_var, text="Notify when a build or pull finishes")
    row(3, "Notifications:", notify_check,
        "Only while the window is not focused." if shutil.which("notify-send")
        else "notify-send is not installed (sudo apt install libnotify-bin), so no notices are shown.")

    storage = ttk.Frame(dialog)
    storage.pack(padx=20, pady=(10, 0), fill=tk.X)
    where = "the desktop keyring" if password_storage() == "keyring" else "~/.docker-gui/config.json (mode 0600)"
    ttk.Label(storage, text=f"Saved sudo password is kept in {where}.", font=("Arial", 8),
              foreground=readable_color("gray"), wraplength=400, justify=tk.LEFT).pack(anchor="w")
    if not docker_needs_sudo():
        ttk.Label(storage, text="Your user can run Docker directly, so no sudo password is needed for it.",
                  font=("Arial", 8), foreground=readable_color("gray"), wraplength=400,
                  justify=tk.LEFT).pack(anchor="w")

    def on_save():
        previous_engine = get_setting("engine")
        set_setting("stats_interval", int(interval_var.get().rstrip("s")))
        set_setting("engine", engine_var.get())
        set_setting("notifications", bool(notify_var.get()))
        set_setting("terminal", terminal_var.get())
        dialog.destroy()
        if engine_var.get() != previous_engine:
            messagebox.showinfo("Settings", "Relaunch the app so every screen uses the new container engine.",
                                parent=root)

    buttons = ttk.Frame(dialog)
    buttons.pack(pady=(14, 18))
    ttk.Button(buttons, text="Save", style="primary.TButton", command=on_save, width=12).pack(side=tk.LEFT, padx=5)
    ttk.Button(buttons, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)
    dialog.bind("<Escape>", lambda e: dialog.destroy())
    _center_dialog(dialog, min_width=480)
