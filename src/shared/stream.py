"""
Session streaming infrastructure for long-running Docker commands.
"""

import tkinter as tk
from tkinter import ttk

from src.docker.operations import stream_docker_cmd, cancel_stream
from src.utils.utils import run_cmd
from src.shared.helpers import _quote


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
