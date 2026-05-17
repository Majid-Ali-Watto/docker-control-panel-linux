"""
Docker GUI Features Module
Complex dialogs and specialized features like pull image, terminal, logs, disk usage.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import shlex
import urllib.request
import urllib.error
import json
import re
from src.utils.utils import run_cmd, async_run, parse_fixed_width_table, clean_subprocess_env
from src.config.config_manager import get_sudo_password
from src.config.config_tooltips import ACTION_TOOLTIPS
from src.docker.docker_actions import check_docker_running
from src.ui.ui_components import create_table_widget, Tooltip
from src.utils.threads import startThreadForTask
from src.docker.docker_operations import run_docker_cmd, stream_docker_cmd, cancel_stream
from src.docker.docker_commands_constants import (
    DOCKER_PULL, DOCKER_IMAGE_PUSH, DOCKER_SEARCH,
    DOCKER_RUN_DETACHED, DOCKER_INSPECT_ANCESTOR,
    DOCKER_DISK_USAGE_VERBOSE, DOCKER_NETWORK_NAMES, DOCKER_IMAGE_BUILD,
    DOCKER_IMAGE_LOAD, DOCKER_VOLUME_CREATE, DOCKER_NETWORK_CREATE,
    DOCKER_COMPOSE_UP
)


def _quote(value):
    return shlex.quote(str(value))


def _split_csv_lines(raw_text):
    values = []
    for line in str(raw_text).splitlines():
        for part in line.split(','):
            part = part.strip()
            if part:
                values.append(part)
    return values


def _join_flag_values(flag, values):
    return ''.join(f" {flag} {_quote(value)}" for value in values if str(value).strip())


def _join_quoted(values):
    return ' '.join(_quote(value) for value in values if str(value).strip())


def _compose_files_to_args(config_files):
    files = _split_csv_lines(config_files)
    return ' '.join(f"-f {_quote(path)}" for path in files)


def _center_dialog(dialog, min_width=420):
    dialog.update_idletasks()
    width = max(dialog.winfo_reqwidth() + 20, min_width)
    height = dialog.winfo_reqheight() + 16
    x = (dialog.winfo_screenwidth() - width) // 2
    y = (dialog.winfo_screenheight() - height) // 2
    dialog.geometry(f"{width}x{height}+{x}+{y}")


_ERROR_HINTS = (
    "error", "failed", "conflict", "permission denied",
    "empty compose file", "not found", "no such",
)

def _make_output_callback(show_text_output_callback, title="", refresh_callback=None, root=None):
    def callback(result):
        text = f"{title}\n\n{result}".strip() if title else result
        show_text_output_callback(text)
        if refresh_callback and root:
            result_lower = result.lower()
            has_error = any(hint in result_lower for hint in _ERROR_HINTS)
            if not has_error:
                root.after(800, refresh_callback)
    return callback


_LATEST_BUILD_SESSION = None
_LATEST_PULL_SESSION = None


def _session_status_text(session):
    if session.get('status') == 'running':
        return "Running..."
    if session.get('status') == 'cancelling':
        return "Cancelling..."
    if session.get('status') == 'cancelled':
        return "Cancelled"
    if session.get('status') == 'completed':
        return "Completed successfully"
    if session.get('status') == 'warning':
        return "Completed, but image was not found"
    if session.get('status') == 'failed':
        return f"Failed (exit code {session.get('return_code')})"
    return "Starting..."


def _refresh_stream_window(session):
    """Sync session state into its current window, if open."""
    window = session.get('window')
    if not window or not window.winfo_exists():
        return

    session['status_var'].set(_session_status_text(session))
    output_text = session['output_text']
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, ''.join(session['output_lines']))
    output_text.see(tk.END)
    output_text.config(state=tk.DISABLED)

    cancel_btn = session['cancel_btn']
    if session.get('status') in ('running', 'cancelling'):
        cancel_btn.config(state=tk.NORMAL if session.get('status') == 'running' else tk.DISABLED)
    else:
        cancel_btn.config(state=tk.DISABLED)

    retry_btn = session.get('retry_btn')
    if retry_btn and retry_btn.winfo_exists():
        if session.get('status') in ('failed', 'warning'):
            retry_btn.pack(side=tk.RIGHT, padx=(0, 12))
        else:
            retry_btn.pack_forget()


def _close_stream_window(session):
    """Close the current stream window without cancelling the session."""
    window = session.get('window')
    if window and window.winfo_exists():
        window.destroy()
    session['window'] = None


def _show_stream_session_window(root, session):
    """Open or reopen a non-modal window for a tracked stream session."""
    existing = session.get('window')
    if existing and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return existing

    window = tk.Toplevel(root)
    window.title(session['title'])
    window.geometry("980x620")

    header = ttk.Frame(window)
    header.pack(fill=tk.X, padx=10, pady=(10, 6))

    ttk.Label(header, text=session['title'], font=("Arial", 11, "bold")).pack(side=tk.LEFT)
    status_var = tk.StringVar(value=_session_status_text(session))
    ttk.Label(header, textvariable=status_var, font=("Arial", 9)).pack(side=tk.RIGHT)

    command_frame = ttk.LabelFrame(window, text="Command", padding=6)
    command_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

    command_text = tk.Text(
        command_frame,
        height=2,
        wrap=tk.WORD,
        font=("JetBrains Mono", 9),
        bg="#20242b",
        fg="#d4d4d4",
        relief=tk.FLAT,
    )
    command_text.pack(fill=tk.X)
    command_text.insert("1.0", session['command'])
    command_text.config(state=tk.DISABLED)

    output_frame = ttk.Frame(window)
    output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

    output_text = tk.Text(
        output_frame,
        wrap=tk.NONE,
        font=("JetBrains Mono", 9),
        bg="#1e1e1e",
        fg="#d4d4d4",
        insertbackground="#d4d4d4",
    )
    output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scroll_y = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=output_text.yview)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    scroll_x = ttk.Scrollbar(output_frame, orient=tk.HORIZONTAL, command=output_text.xview)
    scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    output_text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

    footer = ttk.Frame(window)
    footer.pack(fill=tk.X, padx=10, pady=(0, 10))

    cancel_btn = ttk.Button(footer, text=session.get('cancel_label', 'Cancel'), width=14)
    cancel_btn.pack(side=tk.RIGHT, padx=(0, 12))
    close_btn = ttk.Button(footer, text="Close", width=12)
    close_btn.pack(side=tk.RIGHT, padx=(0, 12))
    retry_btn = ttk.Button(footer, text=session.get('retry_label', 'Retry'), width=12, style="warning.TButton")

    def on_cancel():
        if session.get('status') != 'running' or not session.get('controller'):
            return

        cancelled = cancel_stream(session['controller'])
        if cancelled:
            session['status'] = 'cancelling'
            _refresh_stream_window(session)

    def on_retry():
        retry_cb = session.get('retry_callback')
        if retry_cb:
            retry_cb()

    close_btn.config(command=lambda: _close_stream_window(session))
    cancel_btn.config(command=on_cancel)
    retry_btn.config(command=on_retry)
    window.protocol("WM_DELETE_WINDOW", lambda: _close_stream_window(session))

    session['window'] = window
    session['status_var'] = status_var
    session['output_text'] = output_text
    session['cancel_btn'] = cancel_btn
    session['retry_btn'] = retry_btn
    _refresh_stream_window(session)

    return window


def _verify_built_image_tag(tag, sudo_password=None):
    """Verify that a tagged image exists after build completion."""
    result = run_cmd(f"docker image inspect {_quote(tag)}", sudo=True, sudo_password=sudo_password)
    if result.lstrip().startswith('['):
        return True, f"\nVerified image tag: {tag}\n"
    return False, (
        f"\nBuild command finished, but the image tag '{tag}' was not found in Docker images.\n"
        "Check the build output above and confirm the tag/value used for the build.\n"
    )


def _start_stream_session(root, title, command, sudo=False, sudo_password=None, on_success=None, success_validator=None, cancel_label='Cancel', retry_label='Retry'):
    """Create and start a tracked stream session."""
    session = {
        'root': root,
        'title': title,
        'command': command,
        'sudo': sudo,
        'sudo_password': sudo_password,
        'on_success': on_success,
        'status': 'running',
        'return_code': None,
        'controller': None,
        'output_lines': [],
        'window': None,
        'status_var': None,
        'output_text': None,
        'cancel_btn': None,
        'retry_btn': None,
        'cancel_label': cancel_label,
        'retry_label': retry_label,
    }

    def append_output(line):
        session['output_lines'].append(line)
        _refresh_stream_window(session)

    def mark_complete(full_output, return_code, was_cancelled):
        session['return_code'] = return_code
        if was_cancelled:
            session['status'] = 'cancelled'
            if not full_output.strip():
                session['output_lines'].append("\nBuild cancelled by user.\n")
        elif return_code == 0:
            validation_ok = True
            validation_message = ""
            if success_validator:
                validation_ok, validation_message = success_validator()
                if validation_message:
                    session['output_lines'].append(validation_message)

            if validation_ok:
                session['status'] = 'completed'
                if not full_output.strip():
                    session['output_lines'].append("Build completed successfully.\n")
                if session.get('on_success'):
                    session['on_success']()
            else:
                session['status'] = 'warning'
                if not full_output.strip() and not validation_message:
                    session['output_lines'].append("Build finished, but the expected image was not found.\n")
        else:
            session['status'] = 'failed'
            if not full_output.strip():
                session['output_lines'].append(f"Command failed with exit code {return_code}.\n")
        _refresh_stream_window(session)

    def _start_stream():
        session['controller'] = stream_docker_cmd(
            command,
            sudo=sudo,
            sudo_password=sudo_password,
            output_callback=lambda line: root.after(0, lambda value=line: append_output(value)),
            complete_callback=lambda output, code, was_cancelled: root.after(
                0, lambda: mark_complete(output, code, was_cancelled)
            ),
        )

    def _retry_session():
        session['status'] = 'running'
        session['return_code'] = None
        session['output_lines'] = []
        _refresh_stream_window(session)
        _start_stream()

    session['retry_callback'] = _retry_session
    _start_stream()

    return session


def reopen_latest_build_status_window(root):
    """Reopen the latest build status window if a build session exists."""
    if not _LATEST_BUILD_SESSION:
        messagebox.showinfo("Build Status", "No image build session has been started yet.", parent=root)
        return

    _show_stream_session_window(root, _LATEST_BUILD_SESSION)

    return _LATEST_BUILD_SESSION['window']


def reopen_latest_pull_status_window(root):
    """Reopen the latest pull status window if a pull session exists."""
    if not _LATEST_PULL_SESSION:
        messagebox.showinfo("Pull Status", "No image pull session has been started yet.", parent=root)
        return
    _show_stream_session_window(root, _LATEST_PULL_SESSION)
    return _LATEST_PULL_SESSION['window']


def pull_image_dialog(root, refresh_callback):
    """Pull image from Docker Hub."""
    global _LATEST_PULL_SESSION
    if not check_docker_running(): return

    dialog = tk.Toplevel(root)
    dialog.title("Pull Docker Image")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    ttk.Label(dialog, text="Enter image name (e.g., nginx:latest, mysql:8.0):",
              font=("Arial", 10)).pack(pady=(20, 10), padx=20)

    image_var = tk.StringVar()
    image_entry = ttk.Entry(dialog, textvariable=image_var, font=("Arial", 11), width=40)
    image_entry.pack(pady=5, padx=20)
    image_entry.focus()

    ttk.Label(dialog, text="Leave empty for 'latest' tag",
              font=("Arial", 8), foreground="gray").pack(pady=(0, 4))

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(8, 20))
    ttk.Button(btn_frame, text="Pull", style="primary.TButton", command=lambda: on_pull(), width=12).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    dialog.update_idletasks()
    w = max(dialog.winfo_reqwidth() + 20, 460)
    h = dialog.winfo_reqheight() + 16
    x = (dialog.winfo_screenwidth() - w) // 2
    y = (dialog.winfo_screenheight() - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")

    def on_pull():
        global _LATEST_PULL_SESSION
        image_name = image_var.get().strip()
        if not image_name:
            messagebox.showwarning("Input Required", "Please enter an image name", parent=dialog)
            return
        dialog.destroy()
        command = DOCKER_PULL.format(image_name=_quote(image_name))
        _LATEST_PULL_SESSION = _start_stream_session(
            root,
            title=f"Pull — {image_name}",
            command=command,
            sudo=True,
            sudo_password=get_sudo_password(),
            on_success=refresh_callback,
            cancel_label="Cancel Pull",
            retry_label="Retry Pull",
        )
        _show_stream_session_window(root, _LATEST_PULL_SESSION)

    image_entry.bind("<Return>", lambda e: on_pull())
    image_entry.bind("<Escape>", lambda e: dialog.destroy())


def push_image_dialog(root, image_ref="", refresh_callback=None):
    """Push a Docker image to a registry."""
    if not check_docker_running(): return

    dialog = tk.Toplevel(root)
    dialog.title("Push Docker Image")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    ttk.Label(dialog, text="Image to push (registry/repo:tag):", font=("Arial", 10)).pack(
        pady=(20, 6), padx=20, anchor="w")

    image_var = tk.StringVar(value=image_ref)
    image_entry = ttk.Entry(dialog, textvariable=image_var, font=("Arial", 11), width=46)
    image_entry.pack(pady=(0, 4), padx=20, fill=tk.X)
    image_entry.focus()
    if image_ref:
        image_entry.select_range(0, tk.END)

    ttk.Label(
        dialog,
        text="Examples:  docker.io/username/myimage:1.0   or   myregistry.io/repo:tag",
        font=("Arial", 8), foreground="gray",
    ).pack(padx=20, anchor="w")

    status_label = ttk.Label(dialog, text="", font=("Arial", 9))
    status_label.pack(pady=8)

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(4, 20))
    btn_push = ttk.Button(btn_frame, text="Push", style="primary.TButton", width=12)
    btn_push.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    _center_dialog(dialog, min_width=500)

    def on_push():
        image = image_var.get().strip()
        if not image:
            messagebox.showwarning("Input Required", "Please enter an image name.", parent=dialog)
            return
        btn_push.config(state=tk.DISABLED)
        status_label.config(text="⏳ Pushing image… (this may take a while)", foreground="orange")
        dialog.update()

        def push_task():
            result = run_cmd(
                DOCKER_IMAGE_PUSH.format(image=_quote(image)),
                sudo=True, sudo_password=get_sudo_password(),
            )
            dialog.after(0, lambda: on_push_complete(result))

        startThreadForTask(push_task)

    def on_push_complete(result):
        result_lower = result.lower()
        if any(k in result_lower for k in ("pushed", "digest:", "layer already exists", "latest: digest")):
            status_label.config(text="✅ Image pushed successfully!", foreground="green")
            dialog.after(2000, dialog.destroy)
            if refresh_callback:
                root.after(2100, refresh_callback)
        else:
            btn_push.config(state=tk.NORMAL)
            status_label.config(text="❌ Push failed", foreground="red")
            messagebox.showerror("Push Failed", f"Failed to push image:\n{result[:500]}", parent=dialog)

    btn_push.config(command=on_push)
    image_entry.bind("<Return>", lambda e: on_push())
    image_entry.bind("<Escape>", lambda e: dialog.destroy())


def _format_bytes(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _fetch_hub_size(image_name):
    """Return compressed size of image's latest tag from Docker Hub API, or empty string on failure."""
    name = image_name.split(':')[0]
    tag = image_name.split(':')[1] if ':' in image_name else 'latest'
    namespace, repo = ('library', name) if '/' not in name else name.split('/', 1)
    url = f"https://hub.docker.com/v2/repositories/{namespace}/{repo}/tags/{tag}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'docker-gui/1.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
            size = data.get('full_size', 0)
            return _format_bytes(size) if size else ''
    except Exception:
        return ''


def search_hub_dialog(root, refresh_callback=None, show_text_output=None):
    """Search Docker Hub for images and optionally pull one."""
    if not check_docker_running(): return

    dialog = tk.Toplevel(root)
    dialog.title("Search Docker Hub")
    dialog.transient(root)
    dialog.grab_set()

    _stop_sizes = threading.Event()

    # Search bar
    search_frame = ttk.Frame(dialog)
    search_frame.pack(fill=tk.X, padx=12, pady=(12, 4))

    ttk.Label(search_frame, text="Search:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 6))
    term_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=term_var, font=("Arial", 11))
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    search_entry.focus()
    btn_search = ttk.Button(search_frame, text="🔍 Search", style="primary.TButton", width=12)
    btn_search.pack(side=tk.LEFT, padx=(6, 0))

    status_label = ttk.Label(dialog, text="Type a term and press Search or Enter",
                              font=("Arial", 9), foreground="gray")
    status_label.pack(padx=12, anchor="w", pady=(2, 0))

    # Results table
    table_frame = ttk.Frame(dialog)
    table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 0))

    columns = ("NAME", "DESCRIPTION", "STARS", "OFFICIAL", "SIZE")
    table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
    for col, w in [("NAME", 180), ("DESCRIPTION", 340), ("STARS", 65), ("OFFICIAL", 75), ("SIZE", 95)]:
        table.heading(col, text=col)
        anchor = "center" if col in ("STARS", "OFFICIAL", "SIZE") else "w"
        table.column(col, width=w, minwidth=max(50, w // 2), anchor=anchor)

    scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=table.yview)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    table.configure(yscrollcommand=scroll_y.set)
    table.pack(fill=tk.BOTH, expand=True)

    # Footer
    footer = ttk.Frame(dialog)
    footer.pack(fill=tk.X, padx=12, pady=10)

    btn_pull = ttk.Button(footer, text="⬇ Pull Selected", style="success.TButton", width=16,
                          state=tk.DISABLED)
    btn_pull.pack(side=tk.LEFT)
    ttk.Label(footer, text="Double-click or select + Pull to download",
              font=("Arial", 8), foreground="gray").pack(side=tk.LEFT, padx=10)
    ttk.Button(footer, text="Close", width=10, command=dialog.destroy).pack(side=tk.RIGHT)

    def do_search():
        term = term_var.get().strip()
        if not term:
            messagebox.showwarning("Input Required", "Please enter a search term.", parent=dialog)
            return
        btn_search.config(state=tk.DISABLED)
        btn_pull.config(state=tk.DISABLED)
        status_label.config(text=f"⏳ Searching for '{term}'…", foreground="orange")
        for row in table.get_children():
            table.delete(row)
        dialog.update()

        def search_task():
            result = run_cmd(
                DOCKER_SEARCH.format(term=_quote(term)),
                sudo=True, sudo_password=get_sudo_password(),
            )
            dialog.after(0, lambda: on_search_complete(result, term))

        startThreadForTask(search_task)

    def on_search_complete(result, term):
        _stop_sizes.clear()
        btn_search.config(state=tk.NORMAL)
        rows = []
        for line in result.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 4:
                rows.append(parts[:4])

        if not rows:
            if result.strip() and any(w in result.lower() for w in ('error', 'permission', 'denied', 'failed', 'cannot')):
                status_label.config(text=f"Search error: {result.strip()[:120]}", foreground="red")
            else:
                status_label.config(text=f"No results found for '{term}'", foreground="gray")
            return

        item_ids = []
        for i, row in enumerate(rows):
            tag = 'oddrow' if i % 2 else 'evenrow'
            iid = table.insert("", tk.END, values=row + ['…'], tags=(tag,))
            item_ids.append(iid)
        status_label.config(
            text=f"Found {len(rows)} result(s) — select one and click Pull to download",
            foreground="green",
        )

        image_names = [str(table.item(iid)['values'][0]) for iid in item_ids]

        def _set_size(iid, size):
            try:
                vals = list(table.item(iid)['values'])
                vals[4] = size
                table.item(iid, values=vals)
            except Exception:
                pass

        def fetch_sizes():
            for iid, name in zip(item_ids, image_names):
                if _stop_sizes.is_set():
                    break
                size = _fetch_hub_size(name)
                if _stop_sizes.is_set():
                    break
                try:
                    dialog.after(0, lambda i=iid, s=size or '—': _set_size(i, s))
                except Exception:
                    break

        threading.Thread(target=fetch_sizes, daemon=True).start()

    def on_select(event):
        btn_pull.config(state=tk.NORMAL if table.selection() else tk.DISABLED)

    def do_pull():
        global _LATEST_PULL_SESSION
        sel = table.selection()
        if not sel:
            return
        image_name = str(table.item(sel[0])['values'][0])
        _stop_sizes.set()
        dialog.destroy()
        command = DOCKER_PULL.format(image_name=_quote(image_name))
        _LATEST_PULL_SESSION = _start_stream_session(
            root,
            title=f"Pull — {image_name}",
            command=command,
            sudo=True,
            sudo_password=get_sudo_password(),
            on_success=refresh_callback,
            cancel_label="Cancel Pull",
            retry_label="Retry Pull",
        )
        _show_stream_session_window(root, _LATEST_PULL_SESSION)

    table.bind("<<TreeviewSelect>>", on_select)
    table.bind("<Double-1>", lambda e: do_pull() if table.selection() else None)
    btn_search.config(command=do_search)
    btn_pull.config(command=do_pull)
    search_entry.bind("<Return>", lambda e: do_search())
    search_entry.bind("<Escape>", lambda e: dialog.destroy())

    dialog.update_idletasks()
    w, h = 960, 520
    x = (dialog.winfo_screenwidth() - w) // 2
    y = (dialog.winfo_screenheight() - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")


def build_image_dialog(root, show_text_output_callback, refresh_callback=None):
    """Build a Docker image from a local context directory."""
    if not check_docker_running(): return
    global _LATEST_BUILD_SESSION

    dialog = tk.Toplevel(root)
    dialog.title("Build Docker Image")
    dialog.transient(root)
    dialog.grab_set()

    ttk.Label(dialog, text="Image tag (required):", font=("Arial", 10)).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))
    tag_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=tag_var, width=48).grid(row=0, column=1, columnspan=2, sticky="ew", padx=16, pady=(16, 6))

    ttk.Label(dialog, text="Build context:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=16, pady=6)
    context_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=context_var, width=48).grid(row=1, column=1, sticky="ew", padx=16, pady=6)
    ttk.Button(
        dialog, text="Browse",
        command=lambda: context_var.set(filedialog.askdirectory(parent=dialog) or context_var.get()),
        width=10
    ).grid(row=1, column=2, padx=(0, 16), pady=6)

    ttk.Label(dialog, text="Dockerfile (optional):", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=16, pady=6)
    dockerfile_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=dockerfile_var, width=48).grid(row=2, column=1, sticky="ew", padx=16, pady=6)
    ttk.Button(
        dialog, text="Browse",
        command=lambda: dockerfile_var.set(
            filedialog.askopenfilename(parent=dialog, filetypes=[("Dockerfile", "*"), ("All files", "*.*")]) or dockerfile_var.get()
        ),
        width=10
    ).grid(row=2, column=2, padx=(0, 16), pady=6)

    ttk.Label(dialog, text="Build args (KEY=VALUE, one per line):", font=("Arial", 10)).grid(row=3, column=0, columnspan=3, sticky="w", padx=16, pady=(8, 4))
    build_args_text = tk.Text(dialog, height=5, width=60, font=("JetBrains Mono", 9))
    build_args_text.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=16, pady=(0, 8))

    dialog.columnconfigure(1, weight=1)
    dialog.rowconfigure(4, weight=1)

    def on_build():
        global _LATEST_BUILD_SESSION
        context_path = context_var.get().strip()
        if not context_path:
            messagebox.showwarning("Context Required", "Please choose a build context directory.", parent=dialog)
            return

        tag = tag_var.get().strip()
        if not tag:
            messagebox.showwarning("Tag Required", "Please enter an image tag, for example: myapp:latest", parent=dialog)
            return
        dockerfile_path = dockerfile_var.get().strip()
        build_args = _split_csv_lines(build_args_text.get("1.0", tk.END))

        command = DOCKER_IMAGE_BUILD.format(
            tag=f"-t {_quote(tag)} " if tag else "",
            dockerfile=f"-f {_quote(dockerfile_path)} " if dockerfile_path else "",
            build_args=''.join(f"--build-arg {_quote(item)} " for item in build_args),
            context=_quote(context_path),
        )

        _LATEST_BUILD_SESSION = _start_stream_session(
            root,
            "Docker Image Build",
            command,
            sudo=True,
            sudo_password=get_sudo_password(),
            on_success=lambda: refresh_callback() if refresh_callback else None,
            success_validator=lambda: _verify_built_image_tag(tag, get_sudo_password()),
            cancel_label='Cancel Build',
            retry_label='Retry Build',
        )
        build_window = _show_stream_session_window(root, _LATEST_BUILD_SESSION)
        dialog.destroy()
        build_window.lift()

    btn_frame = ttk.Frame(dialog)
    btn_frame.grid(row=5, column=0, columnspan=3, pady=(8, 16))
    ttk.Button(btn_frame, text="Build", style="primary.TButton", command=on_build, width=12).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    _center_dialog(dialog, min_width=700)


def load_image_dialog(root, show_text_output_callback, refresh_callback=None):
    """Load a Docker image archive from disk."""
    if not check_docker_running(): return

    filename = filedialog.askopenfilename(
        parent=root,
        title="Load Docker Image",
        filetypes=[("Tar archives", "*.tar"), ("All files", "*.*")],
    )
    if not filename:
        return

    command = DOCKER_IMAGE_LOAD.format(input_file=_quote(filename))
    run_docker_cmd(
        command,
        sudo=True,
        sudo_password=get_sudo_password(),
        callback=_make_output_callback(show_text_output_callback, "Image Load", refresh_callback, root),
    )


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

    _center_dialog(dialog, min_width=360)


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


def _parse_conflict_container_ids(output):
    """Return list of container IDs that caused 'name already in use' conflicts."""
    import re
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

    # Validate: file must contain a 'services:' key to be a real compose file
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
            # Extract short container names from error lines for the prompt
            import re
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

        # No conflict — check for other errors
        result_lower = result.lower()
        has_error = any(hint in result_lower for hint in _ERROR_HINTS)
        if not has_error and refresh_callback and root:
            root.after(800, refresh_callback)

    def _remove_and_retry(container_ids):
        from src.utils.threads import startThreadForTask
        from src.utils.utils import run_cmd

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


def browse_container_files_dialog(root, display_manager):
    """Browse the filesystem of a running container with download/upload support."""
    if not check_docker_running(): return

    selection = display_manager.get_selected_items()
    if not selection:
        messagebox.showwarning("No Selection", "Please select a container from the table")
        return
    if len(selection) > 1:
        messagebox.showwarning("Multiple Selection", "Please select only one container")
        return

    values = display_manager.get_item_values(selection[0])
    container_id = values[1]
    container_name = values[2]

    dialog = tk.Toplevel(root)
    dialog.title(f"File Browser — {container_name} ({container_id[:12]})")
    dialog.transient(root)
    dialog.grab_set()

    # ── Nav bar ──────────────────────────────────────────────────
    nav_frame = ttk.Frame(dialog)
    nav_frame.pack(fill=tk.X, padx=10, pady=(10, 4))

    ttk.Label(nav_frame, text="Path:", font=("Arial", 10)).pack(side=tk.LEFT)
    path_var = tk.StringVar(value="/")
    path_entry = ttk.Entry(nav_frame, textvariable=path_var, font=("JetBrains Mono", 10))
    path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 4))
    btn_go = ttk.Button(nav_frame, text="Go", width=5)
    btn_go.pack(side=tk.LEFT, padx=(0, 3))
    btn_up = ttk.Button(nav_frame, text="⬆ Up", width=7)
    btn_up.pack(side=tk.LEFT, padx=(0, 3))
    btn_refresh = ttk.Button(nav_frame, text="🔄", width=4)
    btn_refresh.pack(side=tk.LEFT)

    # ── File table ───────────────────────────────────────────────
    table_frame = ttk.Frame(dialog)
    table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))

    columns = ("name", "perms", "size", "date", "owner")
    table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
    for col, lbl, w, anchor in [
        ("name",  "Name",        240, "w"),
        ("perms", "Permissions", 110, "w"),
        ("size",  "Size",         80, "e"),
        ("date",  "Date",        130, "w"),
        ("owner", "Owner",        90, "w"),
    ]:
        table.heading(col, text=lbl)
        table.column(col, width=w, minwidth=max(50, w // 2), anchor=anchor)

    scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=table.yview)
    scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=table.xview)
    scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    table.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    table.pack(fill=tk.BOTH, expand=True)

    # ── Footer ───────────────────────────────────────────────────
    footer = ttk.Frame(dialog)
    footer.pack(fill=tk.X, padx=10, pady=(0, 10))

    btn_download = ttk.Button(footer, text="⬇ Download", style="success.TButton", width=13,
                              state=tk.DISABLED)
    btn_download.pack(side=tk.LEFT, padx=(0, 4))
    btn_upload = ttk.Button(footer, text="⬆ Upload", style="info.TButton", width=11)
    btn_upload.pack(side=tk.LEFT)
    status_var = tk.StringVar(value="Loading…")
    ttk.Label(footer, textvariable=status_var, font=("Arial", 9),
              foreground="gray").pack(side=tk.LEFT, padx=10)
    ttk.Button(footer, text="Close", width=9, command=dialog.destroy).pack(side=tk.RIGHT)

    # ── State ────────────────────────────────────────────────────
    current_path = ["/"]
    _row_meta = {}  # iid -> {'type': 'd'/'f'/'l', 'name': str}

    def _parse_ls(output):
        entries = []
        for line in output.split('\n'):
            line = line.rstrip()
            if not line or line.startswith('total'):
                continue
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue
            perms = parts[0]
            owner = parts[2]
            size = parts[4]
            date_str = f"{parts[5]} {parts[6]} {parts[7]}"
            name = parts[8]
            if name in ('.', '..'):
                continue
            etype = 'd' if perms.startswith('d') else ('l' if perms.startswith('l') else 'f')
            icon = '📁' if etype == 'd' else ('🔗' if etype == 'l' else '📄')
            entries.append({
                'type': etype,
                'name': name,
                'display': f"{icon} {name}",
                'perms': perms,
                'size': '' if etype == 'd' else size,
                'date': date_str,
                'owner': owner,
            })
        entries.sort(key=lambda e: (0 if e['type'] == 'd' else 1, e['name'].lower()))
        return entries

    def _load_path(path):
        current_path[0] = path
        path_var.set(path)
        status_var.set(f"Loading {path}…")
        btn_download.config(state=tk.DISABLED)
        for row in table.get_children():
            table.delete(row)
        _row_meta.clear()
        dialog.update()

        def task():
            result = run_cmd(f"docker exec {container_id} ls -la {_quote(path)}", sudo=True, sudo_password=get_sudo_password())
            dialog.after(0, lambda: _on_loaded(result, path))

        startThreadForTask(task)

    def _on_loaded(result, path):
        if any(k in result for k in ('Error response from daemon', 'No such container',
                                      'OCI runtime exec failed', 'executable file not found')):
            status_var.set(f"❌ {result.split(chr(10))[0][:100]}")
            return

        entries = _parse_ls(result)
        for i, e in enumerate(entries):
            tag = 'oddrow' if i % 2 else 'evenrow'
            iid = table.insert("", tk.END,
                               values=(e['display'], e['perms'], e['size'], e['date'], e['owner']),
                               tags=(tag,))
            _row_meta[iid] = {'type': e['type'], 'name': e['name']}

        count = len(entries)
        status_var.set(f"{count} item(s)  —  {path}")

    def _go_to(event=None):
        _load_path(path_var.get().strip() or "/")

    def _navigate_up():
        path = current_path[0].rstrip('/')
        parent = path.rsplit('/', 1)[0] or '/'
        _load_path(parent)

    def _on_select(event):
        btn_download.config(state=tk.NORMAL if table.selection() else tk.DISABLED)

    def _on_double_click(event):
        sel = table.selection()
        if not sel:
            return
        meta = _row_meta.get(sel[0])
        if not meta:
            return
        if meta['type'] == 'd':
            base = current_path[0].rstrip('/')
            _load_path(f"{base}/{meta['name']}")
        else:
            _do_download()

    def _do_download():
        sel = table.selection()
        if not sel:
            return
        meta = _row_meta.get(sel[0])
        if not meta:
            return
        raw_name = meta['name'].split(' -> ')[0].strip()
        base = current_path[0].rstrip('/')
        src_path = f"{base}/{raw_name}"
        local_dest = filedialog.asksaveasfilename(
            parent=dialog, title="Save to host",
            initialfile=raw_name.rsplit('/', 1)[-1],
        )
        if not local_dest:
            return
        status_var.set(f"⏳ Copying {raw_name}…")
        dialog.update()

        def task():
            result = run_cmd(f"docker cp {container_id}:{_quote(src_path)} {_quote(local_dest)}", sudo=True, sudo_password=get_sudo_password())
            msg = (f"✅ Saved → {local_dest}" if not result.strip() or result.strip().lower().startswith('successfully')
                   else f"❌ {result[:120]}")
            dialog.after(0, lambda: status_var.set(msg))

        startThreadForTask(task)

    def _do_upload():
        src = filedialog.askopenfilename(parent=dialog, title="Choose file to upload to container")
        if not src:
            return
        dest_path = current_path[0].rstrip('/') + '/'
        fname = src.rsplit('/', 1)[-1]
        status_var.set(f"⏳ Uploading {fname}…")
        dialog.update()

        def task():
            result = run_cmd(f"docker cp {_quote(src)} {container_id}:{_quote(dest_path)}", sudo=True, sudo_password=get_sudo_password())
            dialog.after(0, lambda: (_load_path(current_path[0])
                                     if not result.strip() or result.strip().lower().startswith('successfully')
                                     else status_var.set(f"❌ {result[:120]}")))

        startThreadForTask(task)

    # Wire up
    btn_go.config(command=_go_to)
    btn_up.config(command=_navigate_up)
    btn_refresh.config(command=lambda: _load_path(current_path[0]))
    btn_download.config(command=_do_download)
    btn_upload.config(command=_do_upload)
    table.bind("<<TreeviewSelect>>", _on_select)
    table.bind("<Double-1>", _on_double_click)
    path_entry.bind("<Return>", _go_to)

    dialog.update_idletasks()
    w, h = 780, 500
    x = (dialog.winfo_screenwidth() - w) // 2
    y = (dialog.winfo_screenheight() - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")

    _load_path("/")


def open_container_terminal_dialog(root, display_manager):
    """Open external interactive terminal for selected container"""
    if not check_docker_running(): return
    
    selection = display_manager.get_selected_items()
    if not selection:
        messagebox.showwarning("No Selection", "Please select a container from the table")
        return
    if len(selection) > 1:
        messagebox.showwarning("Multiple Selection", "Please select only one container for terminal access")
        return
    
    values = display_manager.get_item_values(selection[0])
    container_id = values[1]
    container_name = values[2]

    # Directly open external terminal
    import subprocess
    import shutil
    import tempfile
    import os

    sudo_pw = get_sudo_password()

    # Verify the container can accept exec before launching the terminal.
    # Restarting containers appear in the Running list (docker ps shows them as
    # "Up … (Restarting)") but docker exec will fail until the process is stable.
    state = run_cmd(
        f"docker inspect --format='{{{{.State.Status}}}}' {_quote(container_id)}",
        sudo=True, sudo_password=sudo_pw,
    ).strip().strip("'")
    if state != 'running':
        messages = {
            'restarting': (
                f"'{container_name}' is currently restarting.\n\n"
                "It will appear in the running list while it restarts, but a terminal\n"
                "cannot be opened until the container has fully started.\n\n"
                "Wait a few seconds, then try Terminal again."
            ),
            'paused': (
                f"'{container_name}' is paused.\n\nUnpause it first, then try Terminal again."
            ),
            'exited': (
                f"'{container_name}' has stopped.\n\nStart it first, then try Terminal again."
            ),
            'dead': (
                f"'{container_name}' is in a dead state.\n\nRemove and recreate the container."
            ),
            'created': (
                f"'{container_name}' exists but has never been started.\n\nStart it first."
            ),
            'removing': (
                f"'{container_name}' is being removed."
            ),
        }
        msg = messages.get(
            state,
            f"'{container_name}' is not ready for terminal access (state: {state or 'unknown'})."
        )
        messagebox.showwarning("Terminal Unavailable", msg)
        return

    # If the app needs sudo for Docker, build a silent SUDO_ASKPASS helper so
    # that the interactive `docker exec -it` stdin is never touched by sudo's
    # password prompt.  The askpass script is deleted once the session ends.
    askpass_path = None
    if sudo_pw:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as ap:
            ap.write('#!/bin/bash\n')
            ap.write(f'echo {_quote(sudo_pw)}\n')
            askpass_path = ap.name
        os.chmod(askpass_path, 0o700)
        docker_prefix = f'SUDO_ASKPASS={_quote(askpass_path)} sudo -A '
    else:
        docker_prefix = ''

    # Create a temporary script to avoid quoting issues
    cid_q = _quote(container_id)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as script_file:
        script_file.write('#!/bin/bash\n')
        script_file.write(f'echo -ne "\\033]0;{container_name} ({container_id[:12]})\\007"\n')
        prompt = f'{container_name}({container_id[:12]})# '
        script_file.write(f'{docker_prefix}docker exec -it {cid_q} /bin/bash -c \'PS1="{prompt}" exec /bin/bash\' 2>/dev/null || \\\n')
        script_file.write(f'{docker_prefix}docker exec -it {cid_q} /bin/sh -c \'PS1="{prompt}" exec /bin/sh\'\n')
        if askpass_path:
            script_file.write(f'rm -f {_quote(askpass_path)}\n')
        script_file.write('echo ""\n')
        script_file.write('echo "Press Enter to close..."\n')
        script_file.write('read\n')
        script_path = script_file.name

    os.chmod(script_path, 0o755)
    
    title = f'{container_name} ({container_id[:12]})'

    # Try different terminal emulators in preference order.
    # gnome-terminal / tilix are D-Bus based and exit with code 0 immediately —
    # that is treated as success (see wait logic below).
    terminals = [
        # tilix — good modern terminal, installed on this system
        ('tilix', ['tilix',
                   '--title', title,
                   '-e', script_path]),
        # gnome-terminal (also the target of x-terminal-emulator on Ubuntu)
        ('gnome-terminal', ['gnome-terminal',
                            '--title', title,
                            '--', 'bash', script_path]),
        # x-terminal-emulator alternative invocation (xterm-style)
        ('x-terminal-emulator', ['x-terminal-emulator',
                                  '-title', title,
                                  '-e', script_path]),
        # XFCE terminal
        ('xfce4-terminal', ['xfce4-terminal',
                             '--title', title,
                             '-e', script_path]),
        # KDE Konsole
        ('konsole', ['konsole',
                     '-p', f'tabtitle={title}',
                     '-e', script_path]),
        # MATE Terminal
        ('mate-terminal', ['mate-terminal',
                           '--title', title,
                           '-e', script_path]),
        # Terminator
        ('terminator', ['terminator',
                        '-T', title,
                        '-x', script_path]),
        # xterm fallback
        ('xterm', ['xterm', '-title', title, '-e', script_path]),
    ]
    
    success = False
    last_error = None
    
    for term_name, term_cmd in terminals:
        # Check if terminal executable exists (skip 'env' command check)
        check_cmd = term_cmd[2] if term_cmd[0] == 'env' else term_cmd[0]
        if not shutil.which(check_cmd):
            continue
        
        try:
            # Launch terminal with a snap-scrubbed environment so that
            # system GTK/GIO libraries are used instead of snap-internal ones.
            process = subprocess.Popen(
                term_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                cwd=os.path.expanduser('~'),
                env=clean_subprocess_env(),
            )
            
            # Wait briefly to detect immediate failures.
            # D-Bus terminals (gnome-terminal, tilix) fork and exit with code 0
            # almost instantly — that is success, not failure.
            try:
                retcode = process.wait(timeout=0.5)
                if retcode != 0:
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    last_error = f"{term_name}: exited with code {retcode}"
                    if stderr:
                        last_error += f" - {stderr[:100]}"
                    continue
                # retcode == 0: terminal launched (or handed off to D-Bus) cleanly
                success = True
            except subprocess.TimeoutExpired:
                # Still running after timeout — also success
                success = True

            if success:
                def cleanup_script():
                    import time
                    time.sleep(3)
                    try:
                        os.unlink(script_path)
                    except Exception:
                        pass
                    if askpass_path:
                        try:
                            os.unlink(askpass_path)
                        except Exception:
                            pass
                threading.Thread(target=cleanup_script, daemon=True).start()
                break
                
        except FileNotFoundError as e:
            last_error = f"{term_name}: not found"
            continue
        except Exception as e:
            last_error = f"{term_name}: {str(e)}"
            continue
    
    if not success:
        # Clean up script file
        try:
            os.unlink(script_path)
        except OSError:
            pass
            
        # Show fallback dialog
        fallback_cmd = f"docker exec -it {cid_q} /bin/sh"
        
        # Create a dialog with the command to copy
        cmd_dialog = tk.Toplevel(root)
        cmd_dialog.title("Terminal Access")
        cmd_dialog.geometry("650x300")
        cmd_dialog.transient(root)
        cmd_dialog.grab_set()
        
        ttk.Label(cmd_dialog, text="⚠️ Could not launch external terminal", 
                 font=("Arial", 12, "bold")).pack(pady=10)
        
        if last_error:
            error_frame = ttk.Frame(cmd_dialog)
            error_frame.pack(pady=5, padx=20, fill=tk.X)
            ttk.Label(error_frame, text="Error:", font=("Arial", 9, "bold")).pack(anchor='w')
            ttk.Label(error_frame, text=last_error, 
                     font=("Arial", 8), foreground="red", wraplength=600).pack(anchor='w')
            
            # Suggest installing terminals
            ttk.Label(error_frame, text="\n💡 Install a terminal emulator:", 
                     font=("Arial", 9, "bold"), foreground="blue").pack(anchor='w', pady=(10, 0))
            install_cmd = "sudo apt install tilix  # or xfce4-terminal, gnome-terminal"
            install_text = tk.Text(error_frame, height=1, font=("Courier New", 9), wrap=tk.NONE, 
                                  bg="#f0f0f0", relief=tk.FLAT)
            install_text.pack(fill=tk.X, pady=2)
            install_text.insert(1.0, install_cmd)
            install_text.config(state=tk.DISABLED)
        
        ttk.Label(cmd_dialog, text="Copy and run this command in your terminal:", 
                 font=("Arial", 10)).pack(pady=5)
        
        cmd_text = tk.Text(cmd_dialog, height=2, font=("Courier New", 10), wrap=tk.WORD)
        cmd_text.pack(padx=20, pady=10, fill=tk.X)
        cmd_text.insert(1.0, fallback_cmd)
        cmd_text.config(state=tk.DISABLED)
        
        def copy_to_clipboard():
            cmd_dialog.clipboard_clear()
            cmd_dialog.clipboard_append(fallback_cmd)
            copy_btn.config(text="✓ Copied!")
            cmd_dialog.after(2000, lambda: copy_btn.config(text="Copy Command"))
        
        copy_btn = ttk.Button(cmd_dialog, text="Copy Command", command=copy_to_clipboard)
        copy_btn.pack(pady=10)
        
        ttk.Button(cmd_dialog, text="Close", command=cmd_dialog.destroy).pack(pady=5)


def view_container_logs_dialog(root, display_manager):
    """View logs of selected container"""
    if not check_docker_running(): return
    
    selection = display_manager.get_selected_items()
    if not selection:
        messagebox.showwarning("No Selection", "Please select a container from the table")
        return
    if len(selection) > 1:
        messagebox.showwarning("Multiple Selection", "Please select only one container to view logs")
        return
    
    values = display_manager.get_item_values(selection[0])
    container_id = values[1]
    container_name = values[2]
    
    # Create logs window
    logs_window = tk.Toplevel(root)
    logs_window.title(f"Container Logs - {container_name} ({container_id[:12]})")
    logs_window.geometry("1000x600")
    
    # Control frame
    control_frame = ttk.Frame(logs_window)
    control_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
    
    ttk.Label(control_frame, text="Lines:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
    
    lines_var = tk.StringVar(value="100")
    lines_entry = ttk.Entry(control_frame, textvariable=lines_var, width=10)
    lines_entry.pack(side=tk.LEFT, padx=5)
    
    follow_var = tk.BooleanVar(value=False)
    follow_check = ttk.Checkbutton(control_frame, text="Follow (Live)", variable=follow_var)
    follow_check.pack(side=tk.LEFT, padx=10)
    
    timestamps_var = tk.BooleanVar(value=True)
    timestamps_check = ttk.Checkbutton(control_frame, text="Show Timestamps", variable=timestamps_var)
    timestamps_check.pack(side=tk.LEFT, padx=10)

    search_frame = ttk.Frame(logs_window)
    search_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

    ttk.Label(search_frame, text="Search:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))

    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

    search_count_label = ttk.Label(search_frame, text="0 matches", font=("Arial", 9))
    search_count_label.pack(side=tk.RIGHT)
    
    # Logs text area
    logs_frame = ttk.Frame(logs_window)
    logs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    logs_text = tk.Text(logs_frame, wrap=tk.NONE, font=("Courier New", 9), 
                       bg="#1e1e1e", fg="#d4d4d4")
    logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    logs_scroll_y = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=logs_text.yview)
    logs_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    logs_scroll_x = ttk.Scrollbar(logs_frame, orient=tk.HORIZONTAL, command=logs_text.xview)
    logs_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    logs_text.configure(yscrollcommand=logs_scroll_y.set, xscrollcommand=logs_scroll_x.set)
    logs_text.tag_configure("search_match", background="#3f3f46", foreground="#ffffff")
    logs_text.tag_configure("search_current", background="#facc15", foreground="#111827")
    
    # Status label
    status_label = ttk.Label(logs_window, text="", font=("Arial", 9))
    status_label.pack(fill=tk.X, padx=10, pady=(0, 5))
    
    # Button frame
    button_frame = ttk.Frame(logs_window)
    button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    follow_thread = {'running': False, 'thread': None}
    search_state = {'matches': [], 'current_index': -1}
    search_job = {'id': None}

    def update_search_count():
        matches = len(search_state['matches'])
        if matches == 0:
            search_count_label.config(text="0 matches")
        else:
            search_count_label.config(
                text=f"{search_state['current_index'] + 1}/{matches} matches"
            )

    def clear_search_tags():
        logs_text.tag_remove("search_match", "1.0", tk.END)
        logs_text.tag_remove("search_current", "1.0", tk.END)

    def focus_current_match():
        if not search_state['matches']:
            update_search_count()
            return

        start, end = search_state['matches'][search_state['current_index']]
        logs_text.tag_remove("search_current", "1.0", tk.END)
        logs_text.tag_add("search_current", start, end)
        logs_text.mark_set(tk.INSERT, start)
        logs_text.see(start)
        update_search_count()

    def perform_log_search(*_args):
        query = search_var.get().strip()
        previous_match = None

        if search_state['matches'] and 0 <= search_state['current_index'] < len(search_state['matches']):
            previous_match = search_state['matches'][search_state['current_index']][0]

        clear_search_tags()
        search_state['matches'] = []
        search_state['current_index'] = -1

        if not query:
            update_search_count()
            return

        start_pos = "1.0"
        query_length = len(query)

        while True:
            match_start = logs_text.search(query, start_pos, stopindex=tk.END, nocase=True)
            if not match_start:
                break

            match_end = f"{match_start}+{query_length}c"
            search_state['matches'].append((match_start, match_end))
            logs_text.tag_add("search_match", match_start, match_end)
            start_pos = match_end

        if not search_state['matches']:
            update_search_count()
            return

        if previous_match:
            for idx, (match_start, _match_end) in enumerate(search_state['matches']):
                if match_start == previous_match:
                    search_state['current_index'] = idx
                    break

        if search_state['current_index'] == -1:
            search_state['current_index'] = 0

        focus_current_match()

    def schedule_search_refresh():
        if search_job['id'] is not None:
            logs_window.after_cancel(search_job['id'])
        search_job['id'] = logs_window.after(120, _run_scheduled_search)

    def _run_scheduled_search():
        search_job['id'] = None
        perform_log_search()

    def go_to_search_match(step):
        if not search_state['matches']:
            perform_log_search()
            return

        search_state['current_index'] = (search_state['current_index'] + step) % len(search_state['matches'])
        focus_current_match()

    def set_logs_content(content, status_text=None, status_color=None, show_empty_message=True):
        logs_text.config(state=tk.NORMAL)
        logs_text.delete("1.0", tk.END)
        if content:
            logs_text.insert(tk.END, content)
        elif show_empty_message:
            logs_text.insert(tk.END, "(No logs available)")
        logs_text.see(tk.END)
        logs_text.config(state=tk.DISABLED)
        schedule_search_refresh()

        if status_text is not None:
            status_label.config(text=status_text, foreground=status_color or "green")

    def append_log_line(line):
        logs_text.config(state=tk.NORMAL)
        logs_text.insert(tk.END, line)
        logs_text.see(tk.END)
        logs_text.config(state=tk.DISABLED)
        if search_var.get().strip():
            schedule_search_refresh()
    
    def fetch_logs():
        lines = lines_var.get().strip()
        if not lines.isdigit():
            lines = "100"
        
        timestamps_flag = "--timestamps" if timestamps_var.get() else ""
        
        status_label.config(text="⏳ Fetching logs...", foreground="orange")
        logs_text.config(state=tk.NORMAL)
        logs_text.delete(1.0, tk.END)
        logs_text.config(state=tk.DISABLED)
        logs_window.update()
        
        def fetch_task():
            result = run_cmd(f"docker logs {timestamps_flag} --tail {lines} {container_id}", 
                           sudo=True, sudo_password=get_sudo_password())

            logs_window.after(
                0,
                lambda: set_logs_content(
                    result,
                    status_text=f"✓ Logs loaded ({lines} lines)",
                    status_color="green",
                ),
            )
        
        startThreadForTask(fetch_task)
        
    
    def start_follow():
        if follow_thread['running']:
            return
        
        follow_thread['running'] = True
        follow_var.set(True)
        follow_check.config(state=tk.DISABLED)
        refresh_btn.config(state=tk.DISABLED)
        status_label.config(text="📡 Following logs (live)...", foreground="blue")
        
        timestamps_flag = "--timestamps" if timestamps_var.get() else ""
        
        def follow_task():
            process = subprocess.Popen(
                f"sudo -S docker logs {timestamps_flag} --follow {container_id}",
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            process.stdin.write(f"{get_sudo_password()}\n")
            process.stdin.flush()
            
            logs_window.after(0, lambda: set_logs_content("", show_empty_message=False))
            
            try:
                for line in iter(process.stdout.readline, ''):
                    if not follow_thread['running']:
                        process.kill()
                        break

                    logs_window.after(0, lambda value=line: append_log_line(value))
            except (OSError, ValueError):
                pass

            process.kill()
            logs_window.after(0, lambda: status_label.config(text="✓ Stopped following logs", foreground="gray"))
        
        follow_thread['thread'] = threading.Thread(target=follow_task, daemon=True)
        follow_thread['thread'].start()
    
    def stop_follow():
        if follow_thread['running']:
            follow_thread['running'] = False
            follow_var.set(False)
            follow_check.config(state=tk.NORMAL)
            refresh_btn.config(state=tk.NORMAL)
            status_label.config(text="✓ Stopped following logs", foreground="gray")
    
    def toggle_follow():
        if follow_var.get():
            start_follow()
        else:
            stop_follow()
    
    def clear_logs():
        logs_text.config(state=tk.NORMAL)
        logs_text.delete(1.0, tk.END)
        logs_text.config(state=tk.DISABLED)
        schedule_search_refresh()
        status_label.config(text="Logs cleared", foreground="gray")

    def clear_search():
        search_var.set("")
        perform_log_search()
    
    def save_logs():
        filename = filedialog.asksaveasfilename(
            parent=logs_window,
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"{container_name}_logs.log"
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(logs_text.get(1.0, tk.END))
                status_label.config(text=f"✓ Logs saved to {filename}", foreground="green")
            except Exception as e:
                messagebox.showerror("Save Failed", f"Failed to save logs: {str(e)}", parent=logs_window)
    
    refresh_btn = ttk.Button(button_frame, text="🔄 Refresh", command=fetch_logs, width=15)
    refresh_btn.pack(side=tk.LEFT, padx=5)
    
    ttk.Button(search_frame, text="◀ Prev", command=lambda: go_to_search_match(-1), width=10).pack(side=tk.RIGHT, padx=(8, 0))
    ttk.Button(search_frame, text="Next ▶", command=lambda: go_to_search_match(1), width=10).pack(side=tk.RIGHT, padx=(8, 0))
    ttk.Button(search_frame, text="Clear Search", command=clear_search, width=12).pack(side=tk.RIGHT)

    ttk.Button(button_frame, text="📡 Follow/Stop", command=toggle_follow, width=15).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="💾 Save to File", command=save_logs, width=15).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="🗑 Clear", command=clear_logs, width=15).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Close", command=lambda: (stop_follow(), logs_window.destroy()), 
              width=15).pack(side=tk.RIGHT, padx=5)

    search_entry.bind("<KeyRelease>", perform_log_search)
    search_entry.bind("<Return>", lambda e: go_to_search_match(1))
    search_entry.bind("<Shift-Return>", lambda e: go_to_search_match(-1))
    logs_window.bind("<Control-f>", lambda e: search_entry.focus_set() or "break")
    logs_window.bind("<F3>", lambda e: go_to_search_match(1) or "break")
    logs_window.bind("<Shift-F3>", lambda e: go_to_search_match(-1) or "break")
    
    fetch_logs()
    logs_window.protocol("WM_DELETE_WINDOW", lambda: (stop_follow(), logs_window.destroy()))


def docker_disk_usage_view(output_container, loading_callback):
    """Show Docker disk usage in tabbed view"""
    if not check_docker_running(): return
    
    def callback(result):
        # Clear output area
        for widget in output_container.winfo_children():
            widget.pack_forget()
        
        # Create container frame
        disk_usage_frame = ttk.Frame(output_container)
        disk_usage_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add search bar
        search_frame = ttk.Frame(disk_usage_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        search_label = ttk.Label(search_frame, text="🔍 Search:", font=("Arial", 10))
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        disk_search_entry = ttk.Entry(search_frame, font=("Arial", 10))
        disk_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        disk_tables_data = []
        
        def perform_disk_search(*args):
            query = disk_search_entry.get().lower().strip()
            
            for table_widget, original_rows, columns in disk_tables_data:
                for item in table_widget.get_children():
                    table_widget.delete(item)
                
                for row in original_rows:
                    row_text = ' '.join(str(val).lower() for val in row)
                    if query == '' or query in row_text:
                        table_widget.insert("", tk.END, values=row)
        
        disk_search_entry.bind('<KeyRelease>', perform_disk_search)
        
        notebook = ttk.Notebook(disk_usage_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        lines = result.splitlines()
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            if line.startswith("Images space usage"):
                header = lines[i + 2]
                data = []
                i += 3
                while i < len(lines) and lines[i].strip():
                    data.append(lines[i])
                    i += 1
                
                cols, rows = parse_fixed_width_table(data, header)
                tab = ttk.Frame(notebook)
                notebook.add(tab, text="Images")
                table = create_table_widget(tab, cols)
                for r in rows:
                    table.insert("", tk.END, values=r)
                disk_tables_data.append((table, rows, cols))
            
            elif line.startswith("Containers space usage"):
                header = lines[i + 2]
                data = []
                i += 3
                while i < len(lines) and lines[i].strip():
                    data.append(lines[i])
                    i += 1
                
                cols, rows = parse_fixed_width_table(data, header)
                tab = ttk.Frame(notebook)
                notebook.add(tab, text="Containers")
                table = create_table_widget(tab, cols)
                for r in rows:
                    table.insert("", tk.END, values=r)
                disk_tables_data.append((table, rows, cols))
            
            elif line.startswith("Local Volumes space usage"):
                header = lines[i + 2]
                data = []
                i += 3
                while i < len(lines) and lines[i].strip():
                    data.append(lines[i])
                    i += 1
                
                cols, rows = parse_fixed_width_table(data, header)
                tab = ttk.Frame(notebook)
                notebook.add(tab, text="Volumes")
                table = create_table_widget(tab, cols)
                for r in rows:
                    table.insert("", tk.END, values=r)
                disk_tables_data.append((table, rows, cols))
            
            elif line.startswith("Build cache usage"):
                header = lines[i + 2]
                data = []
                i += 3
                while i < len(lines) and lines[i].strip():
                    data.append(lines[i])
                    i += 1
                
                cols, rows = parse_fixed_width_table(data, header)
                tab = ttk.Frame(notebook)
                notebook.add(tab, text="Build Cache")
                table = create_table_widget(tab, cols)
                for r in rows:
                    table.insert("", tk.END, values=r)
                disk_tables_data.append((table, rows, cols))
            
            i += 1
    
    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=True, sudo_password=get_sudo_password(),
             loading_callback=loading_callback)


def setup_text_context_menu(text_widget, root):
    """Setup right-click context menu for text widget"""
    def show_context_menu(event):
        context_menu = tk.Menu(root, tearoff=0)
        context_menu.add_command(label="Copy", command=lambda: text_widget.event_generate("<<Copy>>"))
        context_menu.add_command(label="Select All", command=lambda: text_widget.tag_add(tk.SEL, "1.0", tk.END))
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    text_widget.bind("<Button-3>", show_context_menu)


def setup_table_context_menu(table_widget, root):
    """Setup right-click context menu for table widget"""
    def show_context_menu(event):
        selection = table_widget.selection()
        if not selection:
            return
        
        item = table_widget.selection()[0]
        values = table_widget.item(item)["values"]
        columns = table_widget["columns"]
        
        context_menu = tk.Menu(root, tearoff=0)
        
        for i, col in enumerate(columns):
            if i < len(values):
                value = str(values[i])
                display_value = value[:30] + "..." if len(value) > 30 else value
                context_menu.add_command(
                    label=f"Copy {col}: {display_value}",
                    command=lambda v=value: copy_to_clipboard(root, v)
                )
        
        context_menu.add_separator()
        context_menu.add_command(label="Copy All Selected Rows", 
                               command=lambda: copy_table_rows(root, table_widget))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    table_widget.bind("<Button-3>", show_context_menu)


def copy_to_clipboard(root, text):
    """Copy text to clipboard"""
    root.clipboard_clear()
    root.clipboard_append(str(text))


def copy_table_rows(root, table_widget):
    """Copy selected table rows to clipboard"""
    selection = table_widget.selection()
    if not selection:
        return
    
    columns = table_widget["columns"]
    lines = ["\t".join(str(col) for col in columns)]
    
    for item in selection:
        values = table_widget.item(item)["values"]
        lines.append("\t".join(str(val) for val in values))
    
    text = "\n".join(lines)
    root.clipboard_clear()
    root.clipboard_append(text)


def create_selected_item_actions(action_frame, root, display_manager, refresh_images_callback, show_loading_callback=None):
    """Create action buttons for selected items in tables"""
    from src.config.config_manager import get_sudo_password
    from src.ui.ui_components import confirm_action_dialog
    from src.docker.docker_commands_constants import (
        DOCKER_CONTAINER_START, DOCKER_CONTAINER_STOP, DOCKER_CONTAINER_RESTART,
        DOCKER_CONTAINER_RM, DOCKER_CONTAINER_PAUSE, DOCKER_CONTAINER_UNPAUSE,
        DOCKER_CONTAINER_RENAME, DOCKER_CONTAINER_COMMIT, DOCKER_CONTAINER_INSPECT,
        DOCKER_IMAGE_RM, DOCKER_IMAGE_PUSH, DOCKER_IMAGE_TAG, DOCKER_IMAGE_SAVE, DOCKER_IMAGE_HISTORY,
        DOCKER_IMAGE_INSPECT, DOCKER_VOLUME_RM, DOCKER_VOLUME_INSPECT,
        DOCKER_NETWORK_RM, DOCKER_NETWORK_INSPECT, DOCKER_NETWORK_CONNECT,
        DOCKER_NETWORK_DISCONNECT, DOCKER_COMPOSE_UP, DOCKER_COMPOSE_DOWN,
        DOCKER_COMPOSE_RESTART, DOCKER_COMPOSE_LOGS, DOCKER_COMPOSE_CONFIG,
        DOCKER_COMPOSE_PS
    )

    def _selected_rows(resource_name, table_type=None, allow_multiple=True):
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", f"Please select {resource_name} from the table")
            return None
        if table_type:
            allowed_types = table_type if isinstance(table_type, (tuple, list, set)) else (table_type,)
            if display_manager.current_table_type not in allowed_types:
                expected = ', '.join(allowed_types)
                messagebox.showwarning("Wrong View", f"Select {resource_name} from the {expected} table.")
                return None
        if not allow_multiple and len(selection) > 1:
            messagebox.showwarning("Multiple Selection", f"Please select only one {resource_name}.")
            return None
        return [display_manager.get_item_values(item) for item in selection]

    def _run_output_command(command, title):
        run_docker_cmd(
            command,
            sudo=True,
            sudo_password=get_sudo_password(),
            callback=_make_output_callback(display_manager.show_text_output, title, None, root),
            loading_callback=show_loading_callback,
        )

    def _prompt_value(title, label, initial_value=""):
        dialog = tk.Toplevel(root)
        dialog.title(title)
        dialog.transient(root)
        dialog.grab_set()

        result = {'value': None}
        ttk.Label(dialog, text=label, font=("Arial", 10)).pack(padx=20, pady=(20, 8), anchor="w")
        value_var = tk.StringVar(value=initial_value)
        entry = ttk.Entry(dialog, textvariable=value_var, width=42)
        entry.pack(padx=20, pady=4)
        entry.focus()

        def on_ok():
            value = value_var.get().strip()
            if value:
                result['value'] = value
                dialog.destroy()
            else:
                messagebox.showwarning("Input Required", "Please enter a value.", parent=dialog)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(10, 20))
        ttk.Button(btn_frame, text="OK", style="primary.TButton", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

        entry.bind("<Return>", lambda e: on_ok())
        entry.bind("<Escape>", lambda e: dialog.destroy())
        _center_dialog(dialog, min_width=360)
        dialog.wait_window()
        return result['value']

    def _container_ids(rows):
        return [row[1] for row in rows]

    def _container_name(row):
        return row[2]

    def _image_ref(row):
        repo = row[1]
        tag = row[2]
        image_id = row[3]
        if repo == "<none>" or tag == "<none>":
            return image_id
        return f"{repo}:{tag}"

    def _network_name(row):
        return row[2]

    def _compose_project(row):
        return row[1], row[3]

    def start_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'))
        if not rows:
            return
        _run_output_command(
            DOCKER_CONTAINER_START.format(containers=_join_quoted(_container_ids(rows))),
            "Container Start",
        )

    def stop_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'))
        if not rows:
            return
        _run_output_command(
            DOCKER_CONTAINER_STOP.format(containers=_join_quoted(_container_ids(rows))),
            "Container Stop",
        )

    def restart_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'))
        if not rows:
            return
        _run_output_command(
            DOCKER_CONTAINER_RESTART.format(containers=_join_quoted(_container_ids(rows))),
            "Container Restart",
        )

    def pause_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'))
        if not rows:
            return
        _run_output_command(
            DOCKER_CONTAINER_PAUSE.format(containers=_join_quoted(_container_ids(rows))),
            "Container Pause",
        )

    def unpause_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'))
        if not rows:
            return
        _run_output_command(
            DOCKER_CONTAINER_UNPAUSE.format(containers=_join_quoted(_container_ids(rows))),
            "Container Unpause",
        )

    def rename_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'), allow_multiple=False)
        if not rows:
            return
        new_name = _prompt_value("Rename Container", "New container name:", _container_name(rows[0]))
        if not new_name:
            return
        _run_output_command(
            DOCKER_CONTAINER_RENAME.format(old_name=_quote(rows[0][1]), new_name=_quote(new_name)),
            "Container Rename",
        )

    def delete_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'))
        if not rows:
            return
        count = len(rows)
        msg = f"Delete {count} container(s)?" if count > 1 else f"Delete container {rows[0][1]}?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_output_command(
                DOCKER_CONTAINER_RM.format(containers=_join_quoted(_container_ids(rows))),
                "Container Delete",
            )

    def inspect_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'), allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_CONTAINER_INSPECT.format(container=_quote(rows[0][1])),
            "Container Inspect",
        )

    def commit_selected_container():
        if not check_docker_running(): return
        rows = _selected_rows("container", table_type=('container', 'container_stats'), allow_multiple=False)
        if not rows:
            return
        image_ref = _prompt_value("Commit Container", "New image name (e.g. myapp:snapshot):")
        if not image_ref:
            return
        _run_output_command(
            DOCKER_CONTAINER_COMMIT.format(container=_quote(rows[0][1]), image=_quote(image_ref)),
            "Container Commit",
        )

    def delete_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image')
        if not rows:
            return
        count = len(rows)
        msg = f"Delete {count} image(s)?" if count > 1 else f"Delete image {_image_ref(rows[0])}?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_output_command(
                DOCKER_IMAGE_RM.format(images=' '.join(_quote(row[3]) for row in rows)),
                "Image Delete",
            )

    def tag_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image', allow_multiple=False)
        if not rows:
            return
        target_tag = _prompt_value("Tag Image", "New tag (e.g. repo:tag):")
        if not target_tag:
            return
        _run_output_command(
            DOCKER_IMAGE_TAG.format(source=_quote(_image_ref(rows[0])), target=_quote(target_tag)),
            "Image Tag",
        )

    def push_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image', allow_multiple=False)
        if not rows:
            return
        push_image_dialog(root, image_ref=_image_ref(rows[0]), refresh_callback=refresh_images_callback)

    def save_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image', allow_multiple=False)
        if not rows:
            return
        filename = filedialog.asksaveasfilename(
            parent=root,
            defaultextension=".tar",
            filetypes=[("Tar archives", "*.tar"), ("All files", "*.*")],
            initialfile=f"{rows[0][1].replace('/', '_')}_{rows[0][2]}.tar",
        )
        if not filename:
            return
        _run_output_command(
            DOCKER_IMAGE_SAVE.format(output_file=_quote(filename), image=_quote(_image_ref(rows[0]))),
            "Image Save",
        )

    def inspect_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image', allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_IMAGE_INSPECT.format(image=_quote(_image_ref(rows[0]))),
            "Image Inspect",
        )

    def history_selected_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image', allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_IMAGE_HISTORY.format(image=_quote(_image_ref(rows[0]))),
            "Image History",
        )

    def delete_selected_volume():
        if not check_docker_running(): return
        rows = _selected_rows("volume", table_type='volume')
        if not rows:
            return
        count = len(rows)
        msg = f"Delete {count} volume(s)?" if count > 1 else f"Delete volume {rows[0][1]}?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_output_command(
                DOCKER_VOLUME_RM.format(volumes=' '.join(_quote(row[1]) for row in rows)),
                "Volume Delete",
            )

    def inspect_selected_volume():
        if not check_docker_running(): return
        rows = _selected_rows("volume", table_type='volume', allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_VOLUME_INSPECT.format(volume=_quote(rows[0][1])),
            "Volume Inspect",
        )

    def delete_selected_network():
        if not check_docker_running(): return
        rows = _selected_rows("network", table_type='network')
        if not rows:
            return
        count = len(rows)
        msg = f"Delete {count} network(s)?" if count > 1 else f"Delete network {_network_name(rows[0])}?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_output_command(
                DOCKER_NETWORK_RM.format(networks=' '.join(_quote(_network_name(row)) for row in rows)),
                "Network Delete",
            )

    def inspect_selected_network():
        if not check_docker_running(): return
        rows = _selected_rows("network", table_type='network', allow_multiple=False)
        if not rows:
            return
        _run_output_command(
            DOCKER_NETWORK_INSPECT.format(network=_quote(_network_name(rows[0]))),
            "Network Inspect",
        )

    def connect_selected_network():
        if not check_docker_running(): return
        rows = _selected_rows("network", table_type='network', allow_multiple=False)
        if not rows:
            return
        container_ref = _prompt_value("Connect Network", "Container name or ID:")
        if not container_ref:
            return
        _run_output_command(
            DOCKER_NETWORK_CONNECT.format(network=_quote(_network_name(rows[0])), container=_quote(container_ref)),
            "Network Connect",
        )

    def disconnect_selected_network():
        if not check_docker_running(): return
        rows = _selected_rows("network", table_type='network', allow_multiple=False)
        if not rows:
            return
        container_ref = _prompt_value("Disconnect Network", "Container name or ID:")
        if not container_ref:
            return
        _run_output_command(
            DOCKER_NETWORK_DISCONNECT.format(network=_quote(_network_name(rows[0])), container=_quote(container_ref)),
            "Network Disconnect",
        )

    def run_container_from_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image')
        if not rows:
            return

        images = [_image_ref(row) for row in rows]

        if len(images) > 1:
            count = len(images)
            msg = f"Run container(s) from {count} selected image(s)?"
            if confirm_action_dialog(root, "Confirm", msg):
                commands = ' && '.join(
                    DOCKER_RUN_DETACHED.format(
                        restart_policy="unless-stopped",
                        name="",
                        ports="",
                        envs="",
                        volumes="",
                        network="",
                        extra_args="",
                        image=f" {_quote(image)}",
                        command="",
                    )
                    for image in images
                )
                _run_output_command(commands, "Container Run")
            return

        dialog = tk.Toplevel(root)
        dialog.title("Run Container")
        dialog.transient(root)
        dialog.grab_set()

        ttk.Label(dialog, text=f"Image: {images[0]}", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 10))

        name_var = tk.StringVar()
        restart_var = tk.StringVar(value="unless-stopped")
        network_names = [name for name in run_cmd(DOCKER_NETWORK_NAMES, sudo=True, sudo_password=get_sudo_password()).splitlines() if name.strip()]
        network_var = tk.StringVar(value="")
        command_var = tk.StringVar()

        ttk.Label(dialog, text="Container name:", font=("Arial", 10)).grid(row=1, column=0, sticky="w", padx=16, pady=4)
        ttk.Entry(dialog, textvariable=name_var, width=42).grid(row=1, column=1, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Restart policy:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", padx=16, pady=4)
        ttk.Combobox(dialog, textvariable=restart_var, values=["unless-stopped", "always", "on-failure", "no"], state="readonly", width=20).grid(row=2, column=1, sticky="w", padx=16, pady=4)

        ttk.Label(dialog, text="Network:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=16, pady=4)
        ttk.Combobox(dialog, textvariable=network_var, values=[""] + network_names, state="readonly", width=30).grid(row=3, column=1, sticky="w", padx=16, pady=4)

        ttk.Label(dialog, text="Ports (one per line, e.g. 8080:80):", font=("Arial", 10)).grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4))
        ports_text = tk.Text(dialog, height=3, width=50, font=("JetBrains Mono", 9))
        ports_text.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Environment (KEY=VALUE):", font=("Arial", 10)).grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4))
        env_text = tk.Text(dialog, height=3, width=50, font=("JetBrains Mono", 9))
        env_text.grid(row=7, column=0, columnspan=2, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Volumes (source:/target):", font=("Arial", 10)).grid(row=8, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4))
        volume_text = tk.Text(dialog, height=3, width=50, font=("JetBrains Mono", 9))
        volume_text.grid(row=9, column=0, columnspan=2, sticky="ew", padx=16, pady=4)

        ttk.Label(dialog, text="Command override (optional):", font=("Arial", 10)).grid(row=10, column=0, sticky="w", padx=16, pady=4)
        ttk.Entry(dialog, textvariable=command_var, width=42).grid(row=10, column=1, sticky="ew", padx=16, pady=4)

        dialog.columnconfigure(1, weight=1)

        def on_run():
            ports = _split_csv_lines(ports_text.get("1.0", tk.END))
            envs = _split_csv_lines(env_text.get("1.0", tk.END))
            volumes = _split_csv_lines(volume_text.get("1.0", tk.END))

            command_tail = ""
            custom_command = command_var.get().strip()
            if custom_command:
                try:
                    command_tail = " " + ' '.join(_quote(part) for part in shlex.split(custom_command))
                except ValueError as exc:
                    messagebox.showwarning("Invalid Command", f"Could not parse command override: {exc}", parent=dialog)
                    return

            command = DOCKER_RUN_DETACHED.format(
                restart_policy=_quote(restart_var.get().strip() or "unless-stopped"),
                name=f" --name {_quote(name_var.get().strip())}" if name_var.get().strip() else "",
                ports=_join_flag_values("-p", ports),
                envs=_join_flag_values("-e", envs),
                volumes=_join_flag_values("-v", volumes),
                network=f" --network {_quote(network_var.get().strip())}" if network_var.get().strip() else "",
                extra_args="",
                image=f" {_quote(images[0])}",
                command=command_tail,
            )
            dialog.destroy()
            _run_output_command(command, "Container Run")

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=11, column=0, columnspan=2, pady=(12, 16))
        ttk.Button(btn_frame, text="Run", style="primary.TButton", command=on_run, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

        _center_dialog(dialog, min_width=640)

    def stop_containers_using_image():
        if not check_docker_running(): return
        rows = _selected_rows("image", table_type='image')
        if not rows:
            return

        all_containers = []
        for row in rows:
            containers = run_cmd(DOCKER_INSPECT_ANCESTOR.format(image_id=row[3]), sudo=True, sudo_password=get_sudo_password())
            if containers:
                all_containers.extend(containers.splitlines())

        all_containers = [container for container in all_containers if container.strip()]
        if not all_containers:
            messagebox.showinfo("Info", "No containers found using selected image(s)")
            return

        count = len(all_containers)
        msg = f"Stop {count} container(s) using selected image(s)?"
        if confirm_action_dialog(root, "Confirm", msg):
            _run_output_command(
                DOCKER_CONTAINER_STOP.format(containers=_join_quoted(all_containers)),
                "Stop Containers Using Image",
            )

    def compose_up_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose')
        if not rows:
            return
        commands = []
        for row in rows:
            _project_name, files = _compose_project(row)
            files_arg = _compose_files_to_args(files)
            if files_arg:
                commands.append(DOCKER_COMPOSE_UP.format(files=files_arg))
        if commands:
            _run_output_command(' && '.join(commands), "Compose Up")

    def compose_down_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose')
        if not rows:
            return
        commands = []
        for row in rows:
            _project_name, files = _compose_project(row)
            files_arg = _compose_files_to_args(files)
            if files_arg:
                commands.append(DOCKER_COMPOSE_DOWN.format(files=files_arg))
        if commands:
            _run_output_command(' && '.join(commands), "Compose Down")

    def compose_restart_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose')
        if not rows:
            return
        commands = []
        for row in rows:
            _project_name, files = _compose_project(row)
            files_arg = _compose_files_to_args(files)
            if files_arg:
                commands.append(DOCKER_COMPOSE_RESTART.format(files=files_arg))
        if commands:
            _run_output_command(' && '.join(commands), "Compose Restart")

    def compose_logs_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose', allow_multiple=False)
        if not rows:
            return
        project_name, files = _compose_project(rows[0])
        files_arg = _compose_files_to_args(files)
        if not files_arg:
            messagebox.showwarning("Missing Compose Files", "This project does not expose compose file paths.")
            return
        _run_output_command(
            DOCKER_COMPOSE_LOGS.format(files=files_arg, lines="200"),
            f"Compose Logs - {project_name}",
        )

    def compose_services_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose', allow_multiple=False)
        if not rows:
            return
        project_name, files = _compose_project(rows[0])
        files_arg = _compose_files_to_args(files)
        if not files_arg:
            messagebox.showwarning("Missing Compose Files", "This project does not expose compose file paths.")
            return

        def callback(result):
            import json as _json
            service_rows = []
            try:
                data = _json.loads(result.strip() or "[]")
                for item in data:
                    ports = item.get("Publishers") or item.get("Ports") or ""
                    if isinstance(ports, list):
                        ports = ", ".join(
                            f"{p.get('PublishedPort', '')}:{p.get('TargetPort', '')}/{p.get('Protocol', '')}"
                            for p in ports if p.get("PublishedPort")
                        )
                    service_rows.append([
                        item.get("ID", "")[:12],
                        item.get("Name", ""),
                        item.get("Service", ""),
                        item.get("State", ""),
                        str(ports),
                    ])
            except (_json.JSONDecodeError, TypeError):
                pass
            display_manager.show_table(
                ["CONTAINER ID", "NAME", "SERVICE", "STATE", "PORTS"],
                service_rows,
                'compose_service',
                f"Compose Services - {project_name}",
                False,
            )

        async_run(
            DOCKER_COMPOSE_PS.format(files=files_arg),
            callback,
            sudo=True,
            sudo_password=get_sudo_password(),
            loading_callback=show_loading_callback,
        )

    def compose_inspect_selected():
        if not check_docker_running(): return
        rows = _selected_rows("compose project", table_type='compose', allow_multiple=False)
        if not rows:
            return
        project_name, files = _compose_project(rows[0])
        files_arg = _compose_files_to_args(files)
        if not files_arg:
            messagebox.showwarning("Missing Compose Files", "This project does not expose compose file paths.")
            return
        _run_output_command(
            DOCKER_COMPOSE_CONFIG.format(files=files_arg),
            f"Compose Config - {project_name}",
        )
    
    action_label = ttk.Label(action_frame, text="Actions on selected:",
                            font=("JetBrains Mono", 9, "bold"))

    btn_start_container = ttk.Button(action_frame, text="▶ Start",
                                     style="success.Outline.TButton",
                                     command=start_selected_container)
    Tooltip(btn_start_container, ACTION_TOOLTIPS["start_container"])

    btn_stop_container = ttk.Button(action_frame, text="⏸ Stop",
                                    style="warning.Outline.TButton",
                                    command=stop_selected_container)
    Tooltip(btn_stop_container, ACTION_TOOLTIPS["stop_container"])

    btn_restart_container = ttk.Button(action_frame, text="↻ Restart",
                                       style="warning.Outline.TButton",
                                       command=restart_selected_container)
    Tooltip(btn_restart_container, ACTION_TOOLTIPS["restart_container"])

    btn_pause_container = ttk.Button(action_frame, text="⏸ Pause",
                                     style="secondary.Outline.TButton",
                                     command=pause_selected_container)
    Tooltip(btn_pause_container, ACTION_TOOLTIPS["pause_container"])

    btn_unpause_container = ttk.Button(action_frame, text="▶ Resume",
                                       style="success.Outline.TButton",
                                       command=unpause_selected_container)
    Tooltip(btn_unpause_container, ACTION_TOOLTIPS["unpause_container"])

    btn_delete_container = ttk.Button(action_frame, text="🗑 Delete",
                                      style="danger.Outline.TButton",
                                      command=delete_selected_container)
    Tooltip(btn_delete_container, ACTION_TOOLTIPS["delete_container"])

    btn_rename_container = ttk.Button(action_frame, text="✎ Rename",
                                      style="info.Outline.TButton",
                                      command=rename_selected_container)
    Tooltip(btn_rename_container, ACTION_TOOLTIPS["rename_container"])

    btn_container_terminal = ttk.Button(action_frame, text="💻 Terminal",
                                        style="info.Outline.TButton",
                                        command=lambda: open_container_terminal_dialog(root, display_manager))
    Tooltip(btn_container_terminal, ACTION_TOOLTIPS["container_terminal"])

    btn_view_logs = ttk.Button(action_frame, text="📄 Logs",
                               style="secondary.Outline.TButton",
                               command=lambda: view_container_logs_dialog(root, display_manager))
    Tooltip(btn_view_logs, ACTION_TOOLTIPS["view_logs"])

    btn_inspect_container = ttk.Button(action_frame, text="🔎 Inspect",
                                       style="secondary.Outline.TButton",
                                       command=inspect_selected_container)
    Tooltip(btn_inspect_container, ACTION_TOOLTIPS["inspect_container"])

    btn_commit_container = ttk.Button(action_frame, text="📦 Commit",
                                      style="secondary.Outline.TButton",
                                      command=commit_selected_container)
    Tooltip(btn_commit_container, ACTION_TOOLTIPS["commit_container"])

    btn_browse_files = ttk.Button(action_frame, text="📂 Files",
                                   style="info.Outline.TButton",
                                   command=lambda: browse_container_files_dialog(root, display_manager))
    Tooltip(btn_browse_files, ACTION_TOOLTIPS["browse_files"])

    btn_delete_image = ttk.Button(action_frame, text="🗑 Delete Image",
                                  style="danger.Outline.TButton",
                                  command=delete_selected_image)
    Tooltip(btn_delete_image, ACTION_TOOLTIPS["delete_image"])

    btn_tag_image = ttk.Button(action_frame, text="🏷 Tag",
                               style="info.Outline.TButton",
                               command=tag_selected_image)
    Tooltip(btn_tag_image, ACTION_TOOLTIPS["tag_image"])

    btn_push_image = ttk.Button(action_frame, text="⬆ Push",
                                style="primary.Outline.TButton",
                                command=push_selected_image)
    Tooltip(btn_push_image, ACTION_TOOLTIPS["push_image"])

    btn_save_image = ttk.Button(action_frame, text="💾 Save",
                                style="secondary.Outline.TButton",
                                command=save_selected_image)
    Tooltip(btn_save_image, ACTION_TOOLTIPS["save_image"])

    btn_inspect_image = ttk.Button(action_frame, text="🔎 Inspect Image",
                                   style="secondary.Outline.TButton",
                                   command=inspect_selected_image)
    Tooltip(btn_inspect_image, ACTION_TOOLTIPS["inspect_image"])

    btn_history_image = ttk.Button(action_frame, text="🧱 History",
                                   style="secondary.Outline.TButton",
                                   command=history_selected_image)
    Tooltip(btn_history_image, ACTION_TOOLTIPS["history_image"])

    btn_delete_volume = ttk.Button(action_frame, text="🗑 Delete Volume",
                                   style="danger.Outline.TButton",
                                   command=delete_selected_volume)
    Tooltip(btn_delete_volume, ACTION_TOOLTIPS["delete_volume"])

    btn_inspect_volume = ttk.Button(action_frame, text="🔎 Inspect Volume",
                                    style="secondary.Outline.TButton",
                                    command=inspect_selected_volume)
    Tooltip(btn_inspect_volume, ACTION_TOOLTIPS["inspect_volume"])

    btn_run_container = ttk.Button(action_frame, text="▶ Run from Image",
                                   style="success.Outline.TButton",
                                   command=run_container_from_image)
    Tooltip(btn_run_container, ACTION_TOOLTIPS["run_container"])

    btn_stop_using = ttk.Button(action_frame, text="⏸ Stop Using Image",
                                style="warning.Outline.TButton",
                                command=stop_containers_using_image)
    Tooltip(btn_stop_using, ACTION_TOOLTIPS["stop_using_image"])

    btn_delete_network = ttk.Button(action_frame, text="🗑 Delete Network",
                                    style="danger.Outline.TButton",
                                    command=delete_selected_network)
    Tooltip(btn_delete_network, ACTION_TOOLTIPS["delete_network"])

    btn_inspect_network = ttk.Button(action_frame, text="🔎 Inspect Network",
                                     style="secondary.Outline.TButton",
                                     command=inspect_selected_network)
    Tooltip(btn_inspect_network, ACTION_TOOLTIPS["inspect_network"])

    btn_connect_network = ttk.Button(action_frame, text="🔌 Connect",
                                     style="info.Outline.TButton",
                                     command=connect_selected_network)
    Tooltip(btn_connect_network, ACTION_TOOLTIPS["connect_network"])

    btn_disconnect_network = ttk.Button(action_frame, text="⛔ Disconnect",
                                        style="warning.Outline.TButton",
                                        command=disconnect_selected_network)
    Tooltip(btn_disconnect_network, ACTION_TOOLTIPS["disconnect_network"])

    btn_compose_up = ttk.Button(action_frame, text="▶ Compose Up",
                                style="success.Outline.TButton",
                                command=compose_up_selected)
    Tooltip(btn_compose_up, ACTION_TOOLTIPS["compose_up"])

    btn_compose_down = ttk.Button(action_frame, text="⏹ Compose Down",
                                  style="danger.Outline.TButton",
                                  command=compose_down_selected)
    Tooltip(btn_compose_down, ACTION_TOOLTIPS["compose_down"])

    btn_compose_restart = ttk.Button(action_frame, text="↻ Compose Restart",
                                     style="warning.Outline.TButton",
                                     command=compose_restart_selected)
    Tooltip(btn_compose_restart, ACTION_TOOLTIPS["compose_restart"])

    btn_compose_logs = ttk.Button(action_frame, text="📄 Compose Logs",
                                  style="secondary.Outline.TButton",
                                  command=compose_logs_selected)
    Tooltip(btn_compose_logs, ACTION_TOOLTIPS["compose_logs"])

    btn_compose_services = ttk.Button(action_frame, text="📋 Services",
                                      style="info.Outline.TButton",
                                      command=compose_services_selected)
    Tooltip(btn_compose_services, ACTION_TOOLTIPS["compose_services"])

    btn_compose_inspect = ttk.Button(action_frame, text="🔎 Compose Config",
                                     style="secondary.Outline.TButton",
                                     command=compose_inspect_selected)
    Tooltip(btn_compose_inspect, ACTION_TOOLTIPS["compose_inspect"])
    
    action_buttons = {
        'start': btn_start_container,
        'stop': btn_stop_container,
        'restart': btn_restart_container,
        'pause': btn_pause_container,
        'unpause': btn_unpause_container,
        'delete': btn_delete_container,
        'rename': btn_rename_container,
        'terminal': btn_container_terminal,
        'logs': btn_view_logs,
        'inspect_container': btn_inspect_container,
        'commit': btn_commit_container,
        'browse_files': btn_browse_files,
        'delete_image': btn_delete_image,
        'tag_image': btn_tag_image,
        'push_image': btn_push_image,
        'save_image': btn_save_image,
        'inspect_image': btn_inspect_image,
        'history_image': btn_history_image,
        'delete_volume': btn_delete_volume,
        'inspect_volume': btn_inspect_volume,
        'run': btn_run_container,
        'stop_using': btn_stop_using,
        'delete_network': btn_delete_network,
        'inspect_network': btn_inspect_network,
        'connect_network': btn_connect_network,
        'disconnect_network': btn_disconnect_network,
        'compose_up': btn_compose_up,
        'compose_down': btn_compose_down,
        'compose_restart': btn_compose_restart,
        'compose_logs': btn_compose_logs,
        'compose_services': btn_compose_services,
        'compose_inspect': btn_compose_inspect,
    }
    
    return action_buttons, action_label
