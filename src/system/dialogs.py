"""
System dialogs: live Docker events window.
"""

import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox

from src.docker.actions import check_docker_running
from src.docker.commands import DOCKER_EVENTS
from src.docker.operations import stream_docker_cmd, cancel_stream
from src.config.config_manager import get_sudo_password
from src.ui.rounded import readable_color

_TYPES = ["all", "container", "image", "volume", "network", "daemon"]
_SINCE = {"Live only": "0s", "Last 10 minutes": "10m", "Last hour": "1h", "Last 24 hours": "24h"}
_MAX_LINES = 5000
_BAD_ACTIONS = ("oom", "kill")
_WARN_ACTIONS = ("die", "stop", "destroy")

_window = {"ref": None}


def event_tone(action):
    """'bad' (oom, kill, unhealthy), 'warn' (die, stop, destroy), 'ok' (start, healthy) or None."""
    action = action.strip().lower()
    if action in _BAD_ACTIONS or action.endswith("unhealthy"):
        return "bad"
    if action in _WARN_ACTIONS:
        return "warn"
    if action == "start" or action.endswith("healthy"):
        return "ok"
    return None


def format_event(line):
    """(text, tone) for one line of `docker events --format` output; lines in any other shape
    (daemon messages, errors) are shown as they are."""
    line = line.rstrip("\n")
    parts = line.split("\t")
    if len(parts) < 5:
        return line, None
    stamp, kind, action, actor_id, name = parts[:5]
    try:
        stamp = datetime.fromtimestamp(int(stamp)).strftime("%H:%M:%S")
    except ValueError:
        pass
    label = name if name and name != "<no value>" else actor_id[:12]
    return f"{stamp}  {kind:<10}  {action:<24}  {label}", event_tone(action)


def events_command(event_type, since):
    """The `docker events` command for a type filter ('all' for none) and a --since value."""
    return DOCKER_EVENTS.format(
        since=since, filters="" if event_type == "all" else f" --filter type={event_type}")


def events_dialog(root):
    """Open (or raise) the live events window."""
    if not check_docker_running(): return
    existing = _window["ref"]
    if existing and existing.winfo_exists():
        existing.lift()
        return

    window = tk.Toplevel(root)
    window.title("Docker Events")
    window.geometry("960x560")
    _window["ref"] = window

    controls = ttk.Frame(window)
    controls.pack(fill=tk.X, padx=10, pady=(10, 4))
    ttk.Label(controls, text="Type:").pack(side=tk.LEFT)
    type_var = tk.StringVar(value="all")
    type_box = ttk.Combobox(controls, textvariable=type_var, values=_TYPES, state="readonly", width=12)
    type_box.pack(side=tk.LEFT, padx=(4, 12))
    ttk.Label(controls, text="Since:").pack(side=tk.LEFT)
    since_var = tk.StringVar(value="Last 10 minutes")
    since_box = ttk.Combobox(controls, textvariable=since_var, values=list(_SINCE), state="readonly", width=16)
    since_box.pack(side=tk.LEFT, padx=(4, 12))
    toggle_btn = ttk.Button(controls, width=10)
    toggle_btn.pack(side=tk.LEFT, padx=4)

    body = ttk.Frame(window)
    body.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
    text = tk.Text(body, wrap=tk.NONE, font=("JetBrains Mono", 9), bg="#1e1e1e", fg="#d4d4d4", state=tk.DISABLED)
    scroll_y = ttk.Scrollbar(body, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=scroll_y.set)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    for tone, color in (("bad", "#f87171"), ("warn", "#fbbf24"), ("ok", "#4ade80")):
        text.tag_configure(tone, foreground=color)

    status = ttk.Label(window, text="", font=("Arial", 9))
    status.pack(fill=tk.X, padx=10)
    footer = ttk.Frame(window)
    footer.pack(fill=tk.X, padx=10, pady=(4, 10))

    state = {"controller": None, "token": None, "count": 0}

    def ui(callback):
        try:
            window.after(0, callback)
        except (tk.TclError, RuntimeError):
            pass     # the window (or the app) closed while the stream was still delivering

    def append(line):
        shown, tone = format_event(line)
        text.config(state=tk.NORMAL)
        text.insert(tk.END, shown + "\n", tone or ())
        state["count"] += 1
        if state["count"] > _MAX_LINES:
            text.delete("1.0", "2.0")
            state["count"] -= 1
        text.see(tk.END)
        text.config(state=tk.DISABLED)

    def stop():
        if state["controller"]:
            cancel_stream(state["controller"])
        state["controller"] = state["token"] = None
        toggle_btn.config(text="▶ Start")
        status.config(text="Stopped", foreground=readable_color("gray"))

    def start():
        stop()
        token = state["token"] = object()

        def on_line(line):
            ui(lambda value=line: state["token"] is token and append(value))

        def on_done(_output, code, cancelled):
            def finish():
                if state["token"] is token and not cancelled:
                    state["controller"] = state["token"] = None
                    toggle_btn.config(text="▶ Start")
                    status.config(text=f"Event stream ended (exit code {code})", foreground=readable_color("red"))
            ui(finish)

        state["controller"] = stream_docker_cmd(
            events_command(type_var.get(), _SINCE[since_var.get()]),
            sudo=True, sudo_password=get_sudo_password(),
            output_callback=on_line, complete_callback=on_done)
        toggle_btn.config(text="⏹ Stop")
        status.config(text="📡 Listening for events…", foreground=readable_color("blue"))

    def toggle():
        stop() if state["controller"] else start()

    def clear():
        text.config(state=tk.NORMAL)
        text.delete("1.0", tk.END)
        text.config(state=tk.DISABLED)
        state["count"] = 0

    def save():
        filename = filedialog.asksaveasfilename(
            parent=window, defaultextension=".log", initialfile="docker_events.log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            try:
                with open(filename, "w") as handle:
                    handle.write(text.get("1.0", tk.END))
                status.config(text=f"✓ Saved to {filename}", foreground=readable_color("green"))
            except OSError as exc:
                messagebox.showerror("Save Failed", str(exc), parent=window)

    def close():
        stop()
        window.destroy()

    toggle_btn.config(command=toggle)
    ttk.Button(controls, text="🗑 Clear", command=clear, width=10).pack(side=tk.LEFT, padx=4)
    ttk.Button(controls, text="💾 Save", command=save, width=10).pack(side=tk.LEFT, padx=4)
    ttk.Button(footer, text="Close", command=close, width=12).pack(side=tk.RIGHT)
    type_box.bind("<<ComboboxSelected>>", lambda e: (clear(), start()))
    since_box.bind("<<ComboboxSelected>>", lambda e: (clear(), start()))
    window.protocol("WM_DELETE_WINDOW", close)
    start()
