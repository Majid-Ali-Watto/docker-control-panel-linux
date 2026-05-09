"""
Terminal Panel — embedded general-purpose shell inside the Docker Control Panel.
"""

import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk


class TerminalPanel(tk.Frame):
    """
    An embedded shell terminal: scrollable output + command input with history.
    Commands run in a subprocess shell; 'cd' is handled as a built-in so the
    working directory persists across commands.
    """

    _BG        = "#0d1117"
    _INPUT_BG  = "#161b22"
    _ENTRY_BG  = "#1c2333"
    _PROMPT_FG = "#4ea8f7"
    _CMD_FG    = "#e6edf3"
    _OUT_FG    = "#c9d1d9"
    _ERR_FG    = "#f47174"
    _INFO_FG   = "#6e7f92"

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=self._BG, **kwargs)
        self._cwd = os.path.expanduser("~")
        self._history: list[str] = []
        self._hist_idx = -1
        self._running_proc = None
        self._proc_lock = threading.Lock()
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # Output area
        out_frame = tk.Frame(self, bg=self._BG)
        out_frame.pack(fill=tk.BOTH, expand=True)

        self._output = tk.Text(
            out_frame,
            bg=self._BG, fg=self._OUT_FG,
            font=("JetBrains Mono", 10),
            wrap=tk.NONE,
            insertbackground=self._OUT_FG,
            relief=tk.FLAT, bd=0, padx=12, pady=8,
            state=tk.DISABLED,
        )
        self._output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sy = ttk.Scrollbar(out_frame, orient=tk.VERTICAL, command=self._output.yview)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._output.xview)
        sx.pack(fill=tk.X)
        self._output.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        # Text colour tags
        self._output.tag_configure("prompt", foreground=self._PROMPT_FG)
        self._output.tag_configure("cmd",    foreground=self._CMD_FG,
                                             font=("JetBrains Mono", 10, "bold"))
        self._output.tag_configure("out",    foreground=self._OUT_FG)
        self._output.tag_configure("err",    foreground=self._ERR_FG)
        self._output.tag_configure("info",   foreground=self._INFO_FG,
                                             font=("JetBrains Mono", 9, "italic"))

        # Thin separator
        tk.Frame(self, bg="#21262d", height=1).pack(fill=tk.X)

        # Input bar
        input_bar = tk.Frame(self, bg=self._INPUT_BG, pady=7)
        input_bar.pack(fill=tk.X)

        self._cwd_var = tk.StringVar(value=self._cwd)
        tk.Label(
            input_bar, textvariable=self._cwd_var,
            font=("JetBrains Mono", 9), bg=self._INPUT_BG, fg=self._PROMPT_FG,
        ).pack(side=tk.LEFT, padx=(12, 2))

        tk.Label(
            input_bar, text="$",
            font=("JetBrains Mono", 10, "bold"), bg=self._INPUT_BG, fg=self._PROMPT_FG,
        ).pack(side=tk.LEFT, padx=(0, 8))

        self._cmd_var = tk.StringVar()
        self._entry = tk.Entry(
            input_bar, textvariable=self._cmd_var,
            font=("JetBrains Mono", 10),
            bg=self._ENTRY_BG, fg=self._CMD_FG,
            insertbackground=self._CMD_FG,
            relief=tk.FLAT, bd=5,
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self._entry.focus()

        self._btn_run = tk.Button(
            input_bar, text="Run",
            font=("Arial", 9, "bold"),
            bg="#238636", fg="white",
            activebackground="#2ea043", activeforeground="white",
            relief=tk.FLAT, padx=12, pady=2,
            cursor="hand2",
            command=self._run,
        )
        self._btn_run.pack(side=tk.LEFT, padx=(0, 4))

        self._btn_kill = tk.Button(
            input_bar, text="Kill",
            font=("Arial", 9),
            bg="#b91c1c", fg="white",
            activebackground="#dc2626", activeforeground="white",
            relief=tk.FLAT, padx=10, pady=2,
            cursor="hand2",
            state=tk.DISABLED,
            command=self._kill,
        )
        self._btn_kill.pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(
            input_bar, text="Clear",
            font=("Arial", 9),
            bg="#30363d", fg="#c9d1d9",
            activebackground="#3d444d", activeforeground="white",
            relief=tk.FLAT, padx=10, pady=2,
            cursor="hand2",
            command=self.clear,
        ).pack(side=tk.LEFT, padx=(0, 12))

        # Key bindings
        self._entry.bind("<Return>",    lambda e: self._run())
        self._entry.bind("<Up>",        self._hist_prev)
        self._entry.bind("<Down>",      self._hist_next)
        self._entry.bind("<Control-c>", lambda e: self._kill())
        self._entry.bind("<Control-l>", lambda e: self.clear())

        self._print_welcome()

    # ── Output helpers ───────────────────────────────────────────────────────

    def _append(self, tag: str, text: str):
        self._output.config(state=tk.NORMAL)
        self._output.insert(tk.END, text, tag)
        self._output.see(tk.END)
        self._output.config(state=tk.DISABLED)

    def _print_welcome(self):
        self._append("info", f"  Docker Control Panel — Shell\n")
        self._append("info", f"  Working directory: {self._cwd}\n")
        self._append("info",  "  Up/Down for history  •  Ctrl+C to kill  •  Ctrl+L to clear\n\n")

    # ── Command execution ────────────────────────────────────────────────────

    def _run(self):
        raw = self._cmd_var.get().strip()
        if not raw:
            return

        # Add to history (deduplicate consecutive)
        if not self._history or self._history[-1] != raw:
            self._history.append(raw)
        self._hist_idx = -1
        self._cmd_var.set("")

        # Print prompt line
        short_cwd = self._cwd.replace(os.path.expanduser("~"), "~")
        self._append("prompt", f"{short_cwd} $ ")
        self._append("cmd", raw + "\n")

        # Built-in: cd
        if raw.startswith("cd") and (len(raw) == 2 or raw[2] in (" ", "\t")):
            self._handle_cd(raw)
            return

        # Built-in: clear
        if raw in ("clear", "cls"):
            self.clear()
            return

        # Disable Run, enable Kill
        self._btn_run.config(state=tk.DISABLED)
        self._btn_kill.config(state=tk.NORMAL)
        self._entry.config(state=tk.DISABLED)

        def task():
            try:
                proc = subprocess.Popen(
                    raw,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self._cwd,
                    text=True,
                    bufsize=1,
                )
                with self._proc_lock:
                    self._running_proc = proc

                # Stream stdout and stderr in separate threads
                def _stream(pipe, tag):
                    for line in iter(pipe.readline, ""):
                        self.after(0, lambda l=line, t=tag: self._append(t, l))
                    pipe.close()

                t_out = threading.Thread(target=_stream, args=(proc.stdout, "out"), daemon=True)
                t_err = threading.Thread(target=_stream, args=(proc.stderr, "err"), daemon=True)
                t_out.start()
                t_err.start()
                proc.wait()
                t_out.join()
                t_err.join()

                with self._proc_lock:
                    self._running_proc = None

                rc = proc.returncode
                self.after(0, lambda: self._on_done(rc))

            except Exception as exc:
                self.after(0, lambda e=exc: (
                    self._append("err", f"Error: {e}\n"),
                    self._on_done(1),
                ))

        threading.Thread(target=task, daemon=True).start()

    def _on_done(self, rc: int):
        self._append("out", "\n")
        self._btn_run.config(state=tk.NORMAL)
        self._btn_kill.config(state=tk.DISABLED)
        self._entry.config(state=tk.NORMAL)
        self._entry.focus()

    def _kill(self):
        with self._proc_lock:
            proc = self._running_proc
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
            self._append("err", "\n[Process terminated]\n")
        self._on_done(-1)

    # ── Built-in: cd ─────────────────────────────────────────────────────────

    def _handle_cd(self, cmd: str):
        parts = cmd.split(None, 1)
        target = parts[1].strip() if len(parts) > 1 else os.path.expanduser("~")
        target = os.path.expanduser(target)
        if not os.path.isabs(target):
            target = os.path.join(self._cwd, target)
        target = os.path.normpath(target)

        if os.path.isdir(target):
            self._cwd = target
            self._cwd_var.set(self._cwd.replace(os.path.expanduser("~"), "~"))
            self._append("out", "\n")
        else:
            self._append("err", f"cd: {target}: No such file or directory\n\n")

    # ── History navigation ────────────────────────────────────────────────────

    def _hist_prev(self, event):
        if not self._history:
            return
        if self._hist_idx == -1:
            self._hist_idx = len(self._history) - 1
        elif self._hist_idx > 0:
            self._hist_idx -= 1
        self._cmd_var.set(self._history[self._hist_idx])
        self._entry.icursor(tk.END)

    def _hist_next(self, event):
        if self._hist_idx == -1:
            return
        self._hist_idx += 1
        if self._hist_idx >= len(self._history):
            self._hist_idx = -1
            self._cmd_var.set("")
        else:
            self._cmd_var.set(self._history[self._hist_idx])
        self._entry.icursor(tk.END)

    # ── Public API ────────────────────────────────────────────────────────────

    def clear(self):
        self._output.config(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        self._output.config(state=tk.DISABLED)
        self._print_welcome()

    def focus_input(self):
        self._entry.focus()
