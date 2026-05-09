"""
Docker GUI Features Module
Complex dialogs and specialized features like pull image, terminal, logs, disk usage.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
from src.utils.utils import run_cmd, async_run, parse_fixed_width_table, clean_subprocess_env
from src.config.config_manager import get_sudo_password
from src.config.config_tooltips import ACTION_TOOLTIPS
from src.docker.docker_actions import check_docker_running
from src.ui.ui_components import create_table_widget, Tooltip
from src.utils.threads import startThreadForTask
from src.docker.docker_commands_constants import (
    DOCKER_PULL, DOCKER_RUN_DETACHED, DOCKER_INSPECT_ANCESTOR,
    DOCKER_DISK_USAGE_VERBOSE
)


def pull_image_dialog(root, refresh_callback):
    """Pull image from Docker Hub dialog"""
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

    result_label = ttk.Label(dialog, text="", font=("Arial", 9))
    result_label.pack(pady=6)

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=(8, 20))
    ttk.Button(btn_frame, text="Pull", command=lambda: on_pull(), width=12).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    # Auto-size to fit all widgets, then center
    dialog.update_idletasks()
    w = max(dialog.winfo_reqwidth() + 20, 460)
    h = dialog.winfo_reqheight() + 16
    x = (dialog.winfo_screenwidth() - w) // 2
    y = (dialog.winfo_screenheight() - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")

    def on_pull():
        image_name = image_var.get().strip()
        if not image_name:
            messagebox.showwarning("Input Required", "Please enter an image name", parent=dialog)
            return

        result_label.config(text="⏳ Pulling image...", foreground="orange")
        dialog.update()

        def pull_task():
            result = run_cmd(DOCKER_PULL.format(image_name=image_name), sudo=True, sudo_password=get_sudo_password())
            dialog.after(0, lambda: on_pull_complete(result))

        startThreadForTask(pull_task)

    def on_pull_complete(result):
        if "Downloaded" in result or "up to date" in result or "Status: Image is up to date" in result:
            result_label.config(text="✅ Image pulled successfully!", foreground="green")
            dialog.after(2000, dialog.destroy)
            root.after(2100, refresh_callback)
        else:
            result_label.config(text="❌ Failed to pull image", foreground="red")
            messagebox.showerror("Pull Failed", f"Failed to pull image:\n{result[:500]}", parent=dialog)

    image_entry.bind("<Return>", lambda e: on_pull())
    image_entry.bind("<Escape>", lambda e: dialog.destroy())


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
    
    # Command to run in container
    docker_cmd = f'docker exec -it {container_id} /bin/sh || docker exec -it {container_id} /bin/bash'
    
    # Create a temporary script to avoid quoting issues
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as script_file:
        script_file.write('#!/bin/bash\n')
        # Set terminal title using escape sequences
        script_file.write(f'echo -ne "\\033]0;{container_name} ({container_id[:12]})\\007"\n')
        # script_file.write('echo ""\n')
        # Set custom PS1 prompt with container name and ID, then exec into container
        prompt = f'{container_name}({container_id[:12]})# '
        script_file.write(f'docker exec -it {container_id} /bin/bash -c \'PS1="{prompt}" exec /bin/bash\' 2>/dev/null || \\\n')
        script_file.write(f'docker exec -it {container_id} /bin/sh -c \'PS1="{prompt}" exec /bin/sh\'\n')
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
        except:
            pass
            
        # Show fallback dialog
        fallback_cmd = f"docker exec -it {container_id} /bin/sh"
        
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
            except:
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
    
    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=False, sudo_password=None, 
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


def create_selected_item_actions(action_frame, root, display_manager, refresh_images_callback):
    """Create action buttons for selected items in tables"""
    from src.docker.docker_operations import run_docker_cmd
    from src.config.config_manager import get_sudo_password
    from src.ui.ui_components import confirm_action_dialog
    
    def start_selected_container():
        if not check_docker_running(): return
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a container from the table")
            return
        container_ids = [display_manager.get_item_values(item)[1] for item in selection]
        run_docker_cmd(f"docker start {' '.join(container_ids)}", sudo=True, 
                      sudo_password=get_sudo_password(), callback=display_manager.show_text_output)
    
    def stop_selected_container():
        if not check_docker_running(): return
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a container from the table")
            return
        container_ids = [display_manager.get_item_values(item)[1] for item in selection]
        run_docker_cmd(f"docker stop {' '.join(container_ids)}", sudo=True, 
                      sudo_password=get_sudo_password(), callback=display_manager.show_text_output)
    
    def delete_selected_container():
        if not check_docker_running(): return
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a container from the table")
            return
        container_ids = [display_manager.get_item_values(item)[1] for item in selection]
        count = len(container_ids)
        msg = f"Delete {count} container(s)?" if count > 1 else f"Delete container {container_ids[0]}?"
        if confirm_action_dialog(root, "Confirm", msg):
            run_docker_cmd(f"docker rm -f {' '.join(container_ids)}", sudo=True, 
                          sudo_password=get_sudo_password(), callback=display_manager.show_text_output)
    
    def delete_selected_image():
        if not check_docker_running(): return
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an image from the table")
            return
        image_ids = [display_manager.get_item_values(item)[3] for item in selection]
        count = len(image_ids)
        msg = f"Delete {count} image(s)?" if count > 1 else f"Delete image {image_ids[0]}?"
        if confirm_action_dialog(root, "Confirm", msg):
            run_docker_cmd(f"docker rmi -f {' '.join(image_ids)}", sudo=True, 
                          sudo_password=get_sudo_password(), callback=display_manager.show_text_output)
    
    def delete_selected_volume():
        if not check_docker_running(): return
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a volume from the table")
            return
        volume_names = [display_manager.get_item_values(item)[1] for item in selection]
        count = len(volume_names)
        msg = f"Delete {count} volume(s)?" if count > 1 else f"Delete volume {volume_names[0]}?"
        if confirm_action_dialog(root, "Confirm", msg):
            run_docker_cmd(f"docker volume rm {' '.join(volume_names)}", sudo=True, 
                          sudo_password=get_sudo_password(), callback=display_manager.show_text_output)
    
    def run_container_from_image():
        if not check_docker_running(): return
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an image from the table")
            return
        
        images = []
        for item in selection:
            values = display_manager.get_item_values(item)
            repo = values[1]
            tag = values[2]
            if repo == "<none>" or tag == "<none>":
                image_id = values[3]
                images.append(image_id)
            else:
                images.append(f"{repo}:{tag}")
        
        # For single image, allow name input
        if len(images) == 1:
            dialog = tk.Toplevel(root)
            dialog.title("Run Container")
            dialog.geometry("450x200")
            dialog.resizable(False, False)
            dialog.transient(root)
            dialog.grab_set()
            
            ttk.Label(dialog, text=f"Run container from: {images[0]}", 
                     font=("Arial", 10, "bold")).pack(pady=(20, 10))
            
            ttk.Label(dialog, text="Container name (optional):", 
                     font=("Arial", 10)).pack(pady=(10, 5))
            
            name_var = tk.StringVar()
            name_entry = ttk.Entry(dialog, textvariable=name_var, font=("Arial", 11), width=40)
            name_entry.pack(pady=5)
            name_entry.focus()
            
            ttk.Label(dialog, text="Leave empty for auto-generated name", 
                     font=("Arial", 8), foreground="gray").pack(pady=2)
            
            def on_run():
                container_name = name_var.get().strip()
                name_param = f"--name {container_name} " if container_name else ""
                command = DOCKER_RUN_DETACHED.format(name=name_param, image=images[0])
                dialog.destroy()
                run_docker_cmd(command, sudo=True, sudo_password=get_sudo_password(), 
                              callback=display_manager.show_text_output)
            
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=20)
            ttk.Button(btn_frame, text="Run", command=on_run, width=12).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)
            
            name_entry.bind("<Return>", lambda e: on_run())
            name_entry.bind("<Escape>", lambda e: dialog.destroy())
        else:
            # Multiple images - no name input
            count = len(images)
            msg = f"Run container(s) from {count} image(s)?"
            if confirm_action_dialog(root, "Confirm", msg):
                commands = ' && '.join([DOCKER_RUN_DETACHED.format(name="", image=img) for img in images])
                run_docker_cmd(commands, sudo=True, sudo_password=get_sudo_password(), 
                              callback=display_manager.show_text_output)
    
    def stop_containers_using_image():
        if not check_docker_running(): return
        selection = display_manager.get_selected_items()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an image from the table")
            return
        
        image_ids = [display_manager.get_item_values(item)[3] for item in selection]
        
        all_containers = []
        for img_id in image_ids:
            containers = run_cmd(DOCKER_INSPECT_ANCESTOR.format(image_id=img_id))
            if containers:
                all_containers.extend(containers.split('\n'))
        
        all_containers = [c for c in all_containers if c.strip()]
        
        if not all_containers:
            messagebox.showinfo("Info", "No containers found using selected image(s)")
            return
        
        count = len(all_containers)
        msg = f"Stop {count} container(s) using selected image(s)?"
        if confirm_action_dialog(root, "Confirm", msg):
            run_docker_cmd(f"docker stop {' '.join(all_containers)}", sudo=True, 
                          sudo_password=get_sudo_password(), callback=display_manager.show_text_output)
    
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

    btn_delete_container = ttk.Button(action_frame, text="🗑 Delete",
                                      style="danger.Outline.TButton",
                                      command=delete_selected_container)
    Tooltip(btn_delete_container, ACTION_TOOLTIPS["delete_container"])

    btn_container_terminal = ttk.Button(action_frame, text="💻 Terminal",
                                        style="info.Outline.TButton",
                                        command=lambda: open_container_terminal_dialog(root, display_manager))
    Tooltip(btn_container_terminal, ACTION_TOOLTIPS["container_terminal"])

    btn_view_logs = ttk.Button(action_frame, text="📄 Logs",
                               style="secondary.Outline.TButton",
                               command=lambda: view_container_logs_dialog(root, display_manager))
    Tooltip(btn_view_logs, ACTION_TOOLTIPS["view_logs"])

    btn_delete_image = ttk.Button(action_frame, text="🗑 Delete Image",
                                  style="danger.Outline.TButton",
                                  command=delete_selected_image)
    Tooltip(btn_delete_image, ACTION_TOOLTIPS["delete_image"])

    btn_delete_volume = ttk.Button(action_frame, text="🗑 Delete Volume",
                                   style="danger.Outline.TButton",
                                   command=delete_selected_volume)
    Tooltip(btn_delete_volume, ACTION_TOOLTIPS["delete_volume"])

    btn_run_container = ttk.Button(action_frame, text="▶ Run from Image",
                                   style="success.Outline.TButton",
                                   command=run_container_from_image)
    Tooltip(btn_run_container, ACTION_TOOLTIPS["run_container"])

    btn_stop_using = ttk.Button(action_frame, text="⏸ Stop Using Image",
                                style="warning.Outline.TButton",
                                command=stop_containers_using_image)
    Tooltip(btn_stop_using, ACTION_TOOLTIPS["stop_using_image"])
    
    action_buttons = {
        'start': btn_start_container,
        'stop': btn_stop_container,
        'delete': btn_delete_container,
        'terminal': btn_container_terminal,
        'logs': btn_view_logs,
        'delete_image': btn_delete_image,
        'delete_volume': btn_delete_volume,
        'run': btn_run_container,
        'stop_using': btn_stop_using
    }
    
    return action_buttons, action_label
