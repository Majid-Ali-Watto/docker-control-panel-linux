"""
Container dialogs: file browser, terminal, logs.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import os
import tempfile

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import run_cmd, clean_subprocess_env
from src.utils.threads import startThreadForTask
from src.shared.helpers import _quote


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

    # Nav bar
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

    # File table
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

    # Footer
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

    # State
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

    import shutil

    sudo_pw = get_sudo_password()

    # Verify the container can accept exec before launching the terminal.
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

    terminals = [
        ('tilix', ['tilix', '--title', title, '-e', script_path]),
        ('gnome-terminal', ['gnome-terminal', '--title', title, '--', 'bash', script_path]),
        ('x-terminal-emulator', ['x-terminal-emulator', '-title', title, '-e', script_path]),
        ('xfce4-terminal', ['xfce4-terminal', '--title', title, '-e', script_path]),
        ('konsole', ['konsole', '-p', f'tabtitle={title}', '-e', script_path]),
        ('mate-terminal', ['mate-terminal', '--title', title, '-e', script_path]),
        ('terminator', ['terminator', '-T', title, '-x', script_path]),
        ('xterm', ['xterm', '-title', title, '-e', script_path]),
    ]

    success = False
    last_error = None

    for term_name, term_cmd in terminals:
        check_cmd = term_cmd[2] if term_cmd[0] == 'env' else term_cmd[0]
        if not shutil.which(check_cmd):
            continue

        try:
            process = subprocess.Popen(
                term_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                cwd=os.path.expanduser('~'),
                env=clean_subprocess_env(),
            )

            try:
                retcode = process.wait(timeout=0.5)
                if retcode != 0:
                    stderr = process.stderr.read().decode('utf-8', errors='ignore')
                    last_error = f"{term_name}: exited with code {retcode}"
                    if stderr:
                        last_error += f" - {stderr[:100]}"
                    continue
                success = True
            except subprocess.TimeoutExpired:
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

        except FileNotFoundError:
            last_error = f"{term_name}: not found"
            continue
        except Exception as e:
            last_error = f"{term_name}: {str(e)}"
            continue

    if not success:
        try:
            os.unlink(script_path)
        except OSError:
            pass

        fallback_cmd = f"docker exec -it {cid_q} /bin/sh"

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

    logs_window = tk.Toplevel(root)
    logs_window.title(f"Container Logs - {container_name} ({container_id[:12]})")
    logs_window.geometry("1000x600")

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

    status_label = ttk.Label(logs_window, text="", font=("Arial", 9))
    status_label.pack(fill=tk.X, padx=10, pady=(0, 5))

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
