"""
Commands tab: searchable docker commands, each with its own Copy button.

Two sets (a switch under the search box): "Used by this app" (generated from
src/docker/commands.py, so nothing the app runs is missing) and a general "Reference".
A category dropdown narrows the active set. Click a row or its Copy button to copy a command;
"Copy all" and "Download" use both sets.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.help.help_commands import APP_COMMAND_SECTIONS, COMMAND_SECTIONS, commands_as_text
from src.ui.scroll_frame import ScrollFrame

_DEFAULT_FILENAME = "docker-commands.txt"
_ALL = "All categories"
_BATCH = 14
_SETS = {"app": ("Used by this app", APP_COMMAND_SECTIONS), "ref": ("Reference", COMMAND_SECTIONS)}


class CommandsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._set = "app"
        self._category = _ALL
        self._rows = []             # (frame, set key, section title, searchable text)
        self._headers = {}          # (set key, section title) -> header frame
        self._shown_headers = set()
        self._pending = []

        self._build_toolbar()
        self.footer = ttk.Label(self, text="Click a command to copy it.", font=("Arial", 8), anchor=tk.W)
        self.footer.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(2, 6))
        self.list = ScrollFrame(self, pad=8)
        self.list.pack(fill=tk.BOTH, expand=True)
        self.empty = ttk.Label(self.list.body, text="No commands match your search.", font=("Arial", 10))
        self._built = False
        self.bind("<Map>", self._build_once)    # the rows are only created when the tab is first shown

    # ---- building -------------------------------------------------------------------
    def _build_toolbar(self):
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.query = tk.StringVar()
        ttk.Label(bar, text="🔍").pack(side=tk.LEFT, padx=(2, 4))
        entry = ttk.Entry(bar, textvariable=self.query)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=2)
        entry.bind("<Escape>", lambda _e: self.query.set(""))
        self.query.trace_add("write", lambda *_: self._apply_filter())
        ttk.Button(bar, text="📋 Copy all", style="secondary.TButton",
                   command=lambda: self._copy(commands_as_text(), "Copied all commands.")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="⬇ Download", style="secondary.TButton", command=self._download).pack(side=tk.LEFT)

        row = ttk.Frame(self)
        row.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._set_buttons = {}
        for key, (label, sections) in _SETS.items():
            count = sum(len(items) for _, items in sections)
            button = ttk.Button(row, text=f"{label}  ({count})", command=lambda k=key: self._select_set(k))
            button.pack(side=tk.LEFT, padx=(0, 6))
            self._set_buttons[key] = button
        self.category_var = tk.StringVar(value=_ALL)
        self.category_box = ttk.Combobox(row, textvariable=self.category_var, state="readonly", width=22)
        self.category_box.pack(side=tk.RIGHT)
        self.category_box.bind("<<ComboboxSelected>>", lambda _e: self._select_category(self.category_var.get()))
        self._refresh_categories()

    def _build_once(self, _event=None):
        if self._built:
            return
        self._built = True
        self._pending = [(key, title, command, description)
                         for key, (_label, sections) in _SETS.items()
                         for title, commands in sections for command, description in commands]
        self._add_batch()

    def _add_batch(self):
        """Create the rows a few at a time: hundreds of widgets at once take over a second to map,
        so the tab opens immediately and fills in over the next moments."""
        if not self.winfo_exists():
            return
        for key, section, command, description in self._pending[:_BATCH]:
            if (key, section) not in self._headers:
                self._headers[(key, section)] = self._section_header(key, section)
            entry = (self._row(self.list.body, command, description), key, section,
                     f"{command} {description}".lower())
            self._rows.append(entry)
            self._place(*entry)
        del self._pending[:_BATCH]
        self._refresh_empty()
        if self._pending:
            self.after(5, self._add_batch)

    def _section_header(self, key, section):
        header = ttk.Frame(self.list.body)
        count = len(dict(_SETS[key][1])[section])
        ttk.Label(header, text=f"{section.title()}  ·  {count}", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(12, 2))
        ttk.Separator(header).pack(fill=tk.X)
        return header

    def _row(self, parent, command, description):
        row = ttk.Frame(parent, padding=(2, 5))
        row.columnconfigure(0, weight=1)
        code = ttk.Label(row, text=command, font=("JetBrains Mono", 9, "bold"), anchor=tk.W, justify=tk.LEFT)
        code.grid(row=0, column=0, sticky="ew")
        desc = ttk.Label(row, text=description, font=("Arial", 9), anchor=tk.W, justify=tk.LEFT)
        desc.grid(row=1, column=0, sticky="ew", pady=(1, 0))
        copy_btn = ttk.Button(row, text="Copy", width=8, style="secondary.TButton")
        copy_btn.grid(row=0, column=1, rowspan=2, padx=(8, 0), sticky="n")
        self.list.wrap(code, 100)
        self.list.wrap(desc, 100)

        def copy(_event=None):
            self._copy(command, f"Copied: {command}")
            copy_btn.configure(text="✓ Copied")
            copy_btn.after(1200, lambda: copy_btn.winfo_exists() and copy_btn.configure(text="Copy"))

        copy_btn.configure(command=copy)
        for widget in (row, code, desc):
            widget.bind("<Button-1>", copy)
            widget.configure(cursor="hand2")
        return row

    # ---- behaviour ------------------------------------------------------------------
    def _refresh_categories(self):
        titles = [title.title() for title, _ in _SETS[self._set][1]]
        self.category_box.configure(values=[_ALL] + titles)
        self.category_var.set(_ALL)
        self._category = _ALL
        for key, button in self._set_buttons.items():
            button.configure(style="primary.TButton" if key == self._set else "secondary.TButton")

    def _select_set(self, key):
        self._set = key
        self._refresh_categories()
        self._apply_filter()
        self.list.scroll_to_top()

    def _select_category(self, label):
        self._category = label
        self._apply_filter()
        self.list.scroll_to_top()

    def _matches(self, key, section, haystack):
        if key != self._set or self._category not in (_ALL, section.title()):
            return False
        return all(word in haystack for word in self.query.get().strip().lower().split())

    def _place(self, row, key, section, haystack):
        """Pack `row` (after its section header) when it matches the current set / category / search."""
        if not self._matches(key, section, haystack):
            return
        if (key, section) not in self._shown_headers:
            self._headers[(key, section)].pack(fill=tk.X)
            self._shown_headers.add((key, section))
        row.pack(fill=tk.X)

    def _apply_filter(self):
        if not self._built:
            return
        for header in self._headers.values():
            header.pack_forget()
        self._shown_headers = set()
        for entry in self._rows:
            entry[0].pack_forget()
            self._place(*entry)
        self._refresh_empty()

    def _refresh_empty(self):
        shown = bool(self._shown_headers)
        self.empty.pack_forget()
        if not shown and not self._pending:
            self.empty.pack(pady=30)
        self.footer.configure(text="Click a command to copy it." if shown or self._pending else "")

    def _copy(self, value, message):
        self.clipboard_clear()
        self.clipboard_append(value)
        self.footer.configure(text=message)

    def _download(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Save commands", defaultextension=".txt", initialfile=_DEFAULT_FILENAME,
            filetypes=[("Text file", "*.txt"), ("Markdown", "*.md"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(commands_as_text())
        except OSError as error:
            messagebox.showerror("Save commands", f"Could not save the file:\n{error}", parent=self)
            return
        self.footer.configure(text=f"Saved to {path}")


def build_commands_tab(notebook):
    """Add the Commands tab to `notebook`."""
    tab = CommandsTab(notebook)
    notebook.add(tab, text=" Commands ")
    return tab
