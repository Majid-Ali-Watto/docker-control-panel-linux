"""
Commands tab: the command reference as a Text widget plus a toolbar to copy and download it.

Click a command line to copy that command; "Copy selection" copies highlighted text; "Copy all"
and "Download" use the whole reference.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.help.help_commands import COMMAND_SECTIONS, COMMANDS_TITLE, commands_as_text

_DEFAULT_FILENAME = "docker-commands.txt"


def build_commands_tab(notebook, theme):
    """Add the Commands tab to `notebook`; returns its Text widget (for theme updates)."""
    tab = ttk.Frame(notebook)
    notebook.add(tab, text=" Commands ")

    toolbar = ttk.Frame(tab)
    toolbar.pack(fill=tk.X, padx=6, pady=(6, 2))
    note = ttk.Label(tab, text="Click a command to copy it.", style="secondary.TLabel",
                     font=("Arial", 8), anchor=tk.W)

    body = ttk.Frame(tab)
    text = tk.Text(body, wrap=tk.WORD, font=("JetBrains Mono", 9),
                   bg=theme["text_bg"], fg=theme["text_fg"],
                   relief=tk.FLAT, borderwidth=0, padx=8, pady=6, cursor="arrow")
    scroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=scroll.set)

    def copy(value, message):
        text.clipboard_clear()
        text.clipboard_append(value)
        note.configure(text=message)

    def copy_selection():
        if text.tag_ranges("sel"):
            copy(text.get("sel.first", "sel.last"), "Copied the selected text.")
        else:
            note.configure(text="Select some text first, or click a command to copy it.")

    def download():
        path = filedialog.asksaveasfilename(
            parent=tab, title="Save commands", defaultextension=".txt",
            initialfile=_DEFAULT_FILENAME,
            filetypes=[("Text file", "*.txt"), ("Markdown", "*.md"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(commands_as_text())
        except OSError as error:
            messagebox.showerror("Save commands", f"Could not save the file:\n{error}", parent=tab)
            return
        note.configure(text=f"Saved to {path}")

    for label, handler in (("📋 Copy all", lambda: copy(commands_as_text(), "Copied all commands.")),
                           ("Copy selection", copy_selection),
                           ("⬇ Download", download)):
        ttk.Button(toolbar, text=label, style="secondary.TButton", command=handler).pack(side=tk.LEFT, padx=(0, 6))

    # --- content: one "cmd" tagged line per command, remembered by line number ---
    command_at = {}
    text.tag_configure("title", font=("JetBrains Mono", 10, "bold"))
    text.tag_configure("section", font=("JetBrains Mono", 9, "bold"), spacing1=12, spacing3=4)
    text.tag_configure("cmd", font=("JetBrains Mono", 9, "bold"), spacing1=6)
    text.tag_configure("desc", lmargin1=18, lmargin2=18)
    text.insert(tk.END, COMMANDS_TITLE + "\n", "title")
    for title, commands in COMMAND_SECTIONS:
        text.insert(tk.END, f"── {title} ──\n", "section")
        for command, description in commands:
            command_at[int(text.index(tk.END).split(".")[0]) - 1] = command
            text.insert(tk.END, command + "\n", "cmd")
            text.insert(tk.END, description + "\n", "desc")
    text.configure(state=tk.DISABLED)

    def on_click(event):
        if text.tag_ranges("sel"):          # the user was selecting text, not clicking
            return
        command = command_at.get(int(text.index(f"@{event.x},{event.y}").split(".")[0]))
        if command:
            copy(command, f"Copied: {command}")

    text.tag_bind("cmd", "<ButtonRelease-1>", on_click)
    text.tag_bind("cmd", "<Enter>", lambda _e: text.configure(cursor="hand2"))
    text.tag_bind("cmd", "<Leave>", lambda _e: text.configure(cursor="arrow"))

    note.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 4))
    body.pack(fill=tk.BOTH, expand=True)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    return text
