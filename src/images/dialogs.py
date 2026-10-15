"""
Image dialogs: pull, push, search hub, build, load.
"""

from src.ui.rounded import readable_color
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import urllib.request
import urllib.error
import json

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import run_cmd
from src.utils.threads import startThreadForTask
from src.docker.operations import run_docker_cmd
from src.docker.commands import (
    DOCKER_PULL, DOCKER_IMAGE_PUSH, DOCKER_SEARCH,
    DOCKER_IMAGE_BUILD, DOCKER_IMAGE_LOAD,
)
from src.shared.helpers import _quote, _split_csv_lines, _center_dialog, _make_output_callback
from src.shared.stream import _start_stream_session, _show_stream_session_window, _verify_built_image_tag

_LATEST_BUILD_SESSION = None
_LATEST_PULL_SESSION = None


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
              font=("Arial", 8), foreground=readable_color("gray")).pack(pady=(0, 4))

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
        font=("Arial", 8), foreground=readable_color("gray"),
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
        status_label.config(text="⏳ Pushing image… (this may take a while)", foreground=readable_color("orange"))
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
            status_label.config(text="✅ Image pushed successfully!", foreground=readable_color("green"))
            dialog.after(2000, dialog.destroy)
            if refresh_callback:
                root.after(2100, refresh_callback)
        else:
            btn_push.config(state=tk.NORMAL)
            status_label.config(text="❌ Push failed", foreground=readable_color("red"))
            messagebox.showerror("Push Failed", f"Failed to push image:\n{result[:500]}", parent=dialog)

    btn_push.config(command=on_push)
    image_entry.bind("<Return>", lambda e: on_push())
    image_entry.bind("<Escape>", lambda e: dialog.destroy())


def search_hub_dialog(root, refresh_callback=None, show_text_output=None):
    """Search Docker Hub for images and optionally pull one."""
    if not check_docker_running(): return

    dialog = tk.Toplevel(root)
    dialog.title("Search Docker Hub")
    dialog.transient(root)
    dialog.grab_set()

    _stop_sizes = threading.Event()

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
                              font=("Arial", 9), foreground=readable_color("gray"))
    status_label.pack(padx=12, anchor="w", pady=(2, 0))

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

    footer = ttk.Frame(dialog)
    footer.pack(fill=tk.X, padx=12, pady=10)

    btn_pull = ttk.Button(footer, text="⬇ Pull Selected", style="success.TButton", width=16,
                          state=tk.DISABLED)
    btn_pull.pack(side=tk.LEFT)
    ttk.Label(footer, text="Double-click or select + Pull to download",
              font=("Arial", 8), foreground=readable_color("gray")).pack(side=tk.LEFT, padx=10)
    ttk.Button(footer, text="Close", width=10, command=dialog.destroy).pack(side=tk.RIGHT)

    def do_search():
        term = term_var.get().strip()
        if not term:
            messagebox.showwarning("Input Required", "Please enter a search term.", parent=dialog)
            return
        btn_search.config(state=tk.DISABLED)
        btn_pull.config(state=tk.DISABLED)
        status_label.config(text=f"⏳ Searching for '{term}'…", foreground=readable_color("orange"))
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
                status_label.config(text=f"Search error: {result.strip()[:120]}", foreground=readable_color("red"))
            else:
                status_label.config(text=f"No results found for '{term}'", foreground=readable_color("gray"))
            return

        item_ids = []
        for i, row in enumerate(rows):
            tag = 'oddrow' if i % 2 else 'evenrow'
            iid = table.insert("", tk.END, values=row + ['…'], tags=(tag,))
            item_ids.append(iid)
        status_label.config(
            text=f"Found {len(rows)} result(s) — select one and click Pull to download",
            foreground=readable_color("green"),
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
