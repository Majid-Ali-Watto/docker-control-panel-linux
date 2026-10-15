"""
Image dialogs: pull, push, registry login, search hub, build, load, import, scan.
"""

from src.ui.rounded import readable_color
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import urllib.request
import urllib.error
import json
import re
from tkinter import simpledialog

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import run_cmd
from src.utils.threads import startThreadForTask
from src.docker.operations import run_docker_cmd
from src.docker.commands import (
    DOCKER_PULL, DOCKER_IMAGE_PUSH, DOCKER_IMAGE_TAG, DOCKER_SEARCH,
    DOCKER_IMAGE_BUILD, DOCKER_IMAGE_LOAD, DOCKER_IMAGE_IMPORT, DOCKER_SCOUT_CVES,
    DOCKER_LOGIN, DOCKER_LOGOUT,
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


def hub_name_parts(image):
    """(registry, path) of an image reference; registry is None for Docker Hub. The first part is a
    registry only when it looks like a host (has a dot or a port, or is localhost)."""
    head, sep, rest = image.partition("/")
    if sep and ("." in head or ":" in head or head == "localhost"):
        return (None, rest) if head in ("docker.io", "index.docker.io", "registry-1.docker.io") else (head, rest)
    return None, image


def needs_hub_namespace(image):
    """True for a Docker Hub reference that cannot be pushed: no <username>/ part, or the
    reserved `library/` namespace that only Docker's official images use."""
    registry, path = hub_name_parts(image)
    return registry is None and ("/" not in path or path.startswith("library/"))


def _push_target(image, username):
    """The image reference under <username>/ on Docker Hub."""
    return f"{username}/{hub_name_parts(image)[1].removeprefix('library/')}"


_PUSH_OK = re.compile(r"digest: sha256:[0-9a-f]+ size: \d+")
_PUSH_NOISE = re.compile(r": (Waiting|Preparing|Pushing|Layer already exists|Pushed)\b|^The push refers to")


def push_error_summary(output):
    """The lines that say why a push failed: docker prints one 'Waiting' line per layer first,
    so the reason sits at the end and would be cut off by a length limit."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    reasons = [line for line in lines if not _PUSH_NOISE.search(line)]
    return "\n".join((reasons or lines)[-6:])


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
        text="Examples:  username/myimage:1.0   or   myregistry.io/repo:tag\n"
             "Docker Hub only accepts <your username>/<name>; you are asked for it when it is missing.",
        font=("Arial", 8), foreground=readable_color("gray"), justify=tk.LEFT,
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
        retag_to = None
        if needs_hub_namespace(image):
            username = simpledialog.askstring(
                "Docker Hub username",
                "Docker Hub only accepts images named <username>/<name>.\n"
                f"'{image}' has no username, so it would go to the reserved official-images\n"
                "namespace and be refused.\n\n"
                "Your Docker Hub username (the image is tagged for it, then pushed):",
                parent=dialog)
            if not username or not username.strip():
                return
            retag_to = _push_target(image, username.strip().lower())
        btn_push.config(state=tk.DISABLED)
        status_label.config(text="⏳ Pushing image… (this may take a while)", foreground=readable_color("orange"))
        dialog.update()

        def push_task():
            password = get_sudo_password()
            target = image
            if retag_to:
                tagged = run_cmd(DOCKER_IMAGE_TAG.format(source=_quote(image), target=_quote(retag_to)),
                                 sudo=True, sudo_password=password)
                if tagged:
                    dialog.after(0, lambda: on_push_complete(tagged))
                    return
                target = retag_to
            result = run_cmd(
                DOCKER_IMAGE_PUSH.format(image=_quote(target)),
                sudo=True, sudo_password=password,
            )
            dialog.after(0, lambda: on_push_complete(result))

        startThreadForTask(push_task)

    def on_push_complete(result):
        if _PUSH_OK.search(result):
            status_label.config(text="✅ Image pushed successfully!", foreground=readable_color("green"))
            dialog.after(2000, dialog.destroy)
            if refresh_callback:
                root.after(2100, refresh_callback)
        else:
            btn_push.config(state=tk.NORMAL)
            status_label.config(text="❌ Push failed", foreground=readable_color("red"))
            reason = push_error_summary(result)
            if "insufficient_scope" in result or "denied" in result.lower():
                reason += ("\n\nCheck that you are logged in (Images → Registry) and that the image name "
                           "starts with your Docker Hub username.")
            messagebox.showerror("Push Failed", f"Failed to push image:\n{reason}", parent=dialog)

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

    ttk.Label(dialog, text="Platform (optional):", font=("Arial", 10)).grid(row=3, column=0, sticky="w", padx=16, pady=6)
    platform_var = tk.StringVar()
    platform_entry = ttk.Entry(dialog, textvariable=platform_var, width=48)
    platform_entry.grid(row=3, column=1, columnspan=2, sticky="ew", padx=16, pady=6)
    ttk.Label(dialog, text="e.g. linux/amd64 or linux/arm64", font=("Arial", 8),
              foreground=readable_color("gray")).grid(row=4, column=1, columnspan=2, sticky="w", padx=16)

    ttk.Label(dialog, text="Build args (KEY=VALUE, one per line):", font=("Arial", 10)).grid(row=5, column=0, columnspan=3, sticky="w", padx=16, pady=(8, 4))
    build_args_text = tk.Text(dialog, height=5, width=60, font=("JetBrains Mono", 9))
    build_args_text.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=16, pady=(0, 8))

    dialog.columnconfigure(1, weight=1)
    dialog.rowconfigure(6, weight=1)

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
            build_args=(f"--platform {_quote(platform_var.get().strip())} " if platform_var.get().strip() else "")
            + ''.join(f"--build-arg {_quote(item)} " for item in build_args),
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
    btn_frame.grid(row=7, column=0, columnspan=3, pady=(8, 16))
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


def import_image_dialog(root, show_text_output_callback, refresh_callback=None):
    """Create an image from a container export tar (docker export → docker import)."""
    if not check_docker_running(): return

    filename = filedialog.askopenfilename(
        parent=root,
        title="Import Container Export",
        filetypes=[("Tar archives", "*.tar"), ("All files", "*.*")],
    )
    if not filename:
        return
    image = simpledialog.askstring(
        "Import Image", "Name for the new image (e.g. myapp:imported):", parent=root)
    if not image or not image.strip():
        return

    run_docker_cmd(
        DOCKER_IMAGE_IMPORT.format(input_file=_quote(filename), image=_quote(image.strip())),
        sudo=True,
        sudo_password=get_sudo_password(),
        callback=_make_output_callback(show_text_output_callback, "Image Import", refresh_callback, root),
    )


# Trivy is the fallback scanner; it is run inline, so it is listed in help_commands._EXTRA_APP_COMMANDS
_TRIVY_IMAGE = "trivy image {image}"
_SCANNER_MISSING = ("unknown command", "not a docker command", "trivy: not found", "trivy: command not found")


def _scanner_missing(output):
    lowered = output.lower()
    return any(hint in lowered for hint in _SCANNER_MISSING)


def scan_image(root, image, show_text_output_callback, show_loading_callback=None):
    """Scan an image for vulnerabilities with `docker scout`, or `trivy` when scout is missing."""
    if not check_docker_running(): return

    def task():
        if show_loading_callback:
            show_loading_callback(True)
        password = get_sudo_password()
        tool, output = "docker scout", run_cmd(
            DOCKER_SCOUT_CVES.format(image=_quote(image)), sudo=True, sudo_password=password)
        if _scanner_missing(output):
            tool, output = "trivy", run_cmd(
                _TRIVY_IMAGE.format(image=_quote(image)), sudo=True, sudo_password=password)
        if _scanner_missing(output):
            text = ("No vulnerability scanner is installed.\n\n"
                    "Install one of:\n"
                    "  • Docker Scout   https://docs.docker.com/scout/install/\n"
                    "  • Trivy          https://trivy.dev/latest/getting-started/installation/")
        else:
            text = f"Vulnerability scan - {image}  ({tool})\n\n{output}"
        if show_loading_callback:
            show_loading_callback(False)
        root.after(0, lambda: show_text_output_callback(text))

    startThreadForTask(task)


# `docker login` writes here; read inside the same shell/sudo context as the login itself
_DOCKER_CONFIG_CAT = "sh -c 'cat \"${DOCKER_CONFIG:-$HOME/.docker}/config.json\" 2>/dev/null'"


def parse_registries(config_text):
    """Registries listed under "auths" in a docker config.json (empty when unreadable)."""
    try:
        auths = json.loads(config_text).get("auths", {})
    except (ValueError, AttributeError):
        return []
    if not isinstance(auths, dict):
        return []
    # Docker Hub also stores its OAuth tokens as pseudo-entries ".../access-token"; they are not registries
    return sorted(name for name in auths if not name.endswith(("/access-token", "/refresh-token")))


def registry_dialog(root):
    """Log in to / out of a registry. The password goes to docker on stdin, never into the command line."""
    if not check_docker_running(): return

    dialog = tk.Toplevel(root)
    dialog.title("Registry Login")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    form = ttk.Frame(dialog)
    form.pack(padx=20, pady=(18, 6), fill=tk.X)
    form.columnconfigure(1, weight=1)

    registry_var, user_var, password_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
    ttk.Label(form, text="Registry:", font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=4)
    registry_box = ttk.Combobox(form, textvariable=registry_var, width=38)
    registry_box.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)
    ttk.Label(form, text="Empty = Docker Hub. Others: ghcr.io, registry.example.com:5000",
              font=("Arial", 8), foreground=readable_color("gray")).grid(row=1, column=1, sticky="w", padx=(10, 0))
    ttk.Label(form, text="Username:", font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=4)
    user_entry = ttk.Entry(form, textvariable=user_var, width=40)
    user_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=4)
    ttk.Label(form, text="Password / token:", font=("Arial", 10)).grid(row=3, column=0, sticky="w", pady=4)
    password_entry = ttk.Entry(form, textvariable=password_var, show="*", width=40)
    password_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=4)

    logged_in_label = ttk.Label(dialog, text="Checking logins…", font=("Arial", 9), wraplength=440, justify=tk.LEFT)
    logged_in_label.pack(padx=20, pady=(8, 2), anchor="w")
    status_label = ttk.Label(dialog, text="", font=("Arial", 9), wraplength=440, justify=tk.LEFT)
    status_label.pack(padx=20, pady=(2, 6), anchor="w")

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(4, 18))
    buttons = []

    def refit():
        """Resize to the content: the login result can be several lines long."""
        if dialog.winfo_exists():
            dialog.geometry("")
            _center_dialog(dialog, min_width=520)

    def registry_arg():
        registry = registry_var.get().strip()
        return f" {_quote(registry)}" if registry else ""

    def set_registries(names):
        if not dialog.winfo_exists():
            return
        registry_box.configure(values=names)
        logged_in_label.config(text=("Logged in to: " + ", ".join(names)) if names
                               else "Not logged in to any registry.")
        refit()

    def refresh_registries():
        def task():
            text = run_cmd(_DOCKER_CONFIG_CAT, sudo=True, sudo_password=get_sudo_password())
            names = parse_registries(text)
            dialog.after(0, lambda: set_registries(names))
        startThreadForTask(task)

    def run(command, password=None, ok_text=None):
        for button in buttons:
            button.config(state=tk.DISABLED)
        status_label.config(text="⏳ Working…", foreground=readable_color("orange"))

        def task():
            result = run_cmd(command, sudo=True, sudo_password=get_sudo_password(),
                             input_text=None if password is None else password + "\n")
            dialog.after(0, lambda: done(result))

        def done(result):
            if not dialog.winfo_exists():
                return
            for button in buttons:
                button.config(state=tk.NORMAL)
            failed = any(word in result.lower() for word in ("error", "denied", "unauthorized", "failed"))
            status_label.config(text=result or ok_text or "Done",
                                foreground=readable_color("red" if failed else "green"))
            password_var.set("")
            refit()
            refresh_registries()

        startThreadForTask(task)

    def on_login():
        if not user_var.get().strip() or not password_var.get():
            messagebox.showwarning("Input Required", "Enter a username and a password or token.", parent=dialog)
            return
        run(DOCKER_LOGIN.format(username=_quote(user_var.get().strip()), registry=registry_arg()),
            password=password_var.get(), ok_text="Login Succeeded")

    def on_logout():
        run(DOCKER_LOGOUT.format(registry=registry_arg()), ok_text="Logged out")

    login_btn = ttk.Button(btn_frame, text="Login", style="primary.TButton", command=on_login, width=12)
    logout_btn = ttk.Button(btn_frame, text="Logout", style="warning.Outline.TButton", command=on_logout, width=12)
    buttons.extend([login_btn, logout_btn])
    login_btn.pack(side=tk.LEFT, padx=5)
    logout_btn.pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Close", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    password_entry.bind("<Return>", lambda e: on_login())
    dialog.bind("<Escape>", lambda e: dialog.destroy())
    user_entry.focus()
    _center_dialog(dialog, min_width=520)
    refresh_registries()


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
