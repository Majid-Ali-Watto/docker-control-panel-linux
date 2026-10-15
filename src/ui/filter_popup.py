"""
Filter popup: a small panel that drops down under the toolbar's filter button.

Edits are held in the popup's own variables and only reach the table on "Apply";
"Clear filters" resets everything. The owner closes the popup on clicks elsewhere.
"""

import tkinter as tk
from tkinter import ttk

from src.ui.rounded import readable_color

CUSTOM_RANGE = "Custom range"


class FilterPopup(tk.Toplevel):
    def __init__(self, anchor, presets, preset, date_from, date_to, pick_date, on_apply, on_clear):
        """``pick_date(var, end_of_day)`` fills a From/To variable from the calendar dialog;
        ``on_apply(preset, date_from, date_to)`` and ``on_clear()`` receive the user's choice."""
        top = anchor.winfo_toplevel()
        super().__init__(top)
        self.overrideredirect(True)
        self.transient(top)
        self.configure(highlightthickness=1, highlightbackground=readable_color("#8a8a8a", 3))
        self._anchor = anchor
        self._on_apply, self._on_clear, self._pick_date = on_apply, on_clear, pick_date
        self._preset = tk.StringVar(master=self, value=preset)
        self._from = tk.StringVar(master=self, value=date_from)
        self._to = tk.StringVar(master=self, value=date_to)

        font = ("Arial", 10)
        body = ttk.Frame(self, padding=12)
        body.pack()
        ttk.Label(body, text="Filters", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(body, text="Created", font=font).grid(row=1, column=0, sticky="w", pady=(10, 0))
        combo = ttk.Combobox(body, textvariable=self._preset, values=presets, state="readonly",
                             font=font, width=16)
        combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(10, 0))
        combo.bind("<<ComboboxSelected>>", lambda _e: self._sync_custom_rows())

        self._custom = ttk.Frame(body)
        self._custom.grid(row=2, column=0, columnspan=2, sticky="ew")
        for row, (text, var, end) in enumerate((("From", self._from, False), ("To", self._to, True))):
            ttk.Label(self._custom, text=text, font=font).grid(row=row, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(self._custom, textvariable=var, font=font, width=17).grid(
                row=row, column=1, padx=(8, 0), pady=(8, 0))
            ttk.Button(self._custom, text="Pick…", style="secondary.TButton", width=7,
                       command=lambda v=var, e=end: self._pick_date(v, end_of_day=e)).grid(
                row=row, column=2, padx=(5, 0), pady=(8, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(buttons, text="Clear filters", style="secondary.Outline.TButton",
                   command=self._clear).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Apply", command=self._apply).pack(side=tk.RIGHT)

        self.bind("<Escape>", lambda _e: self.close())
        self._sync_custom_rows()
        self.focus_force()

    def _sync_custom_rows(self):
        """From/To only apply to "Custom range"; keep the popup anchored under its button."""
        if self._preset.get() == CUSTOM_RANGE:
            self._custom.grid()
        else:
            self._custom.grid_remove()
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        x = self._anchor.winfo_rootx()
        if x + self.winfo_reqwidth() > screen_width:   # near the right edge: line up the right sides
            x = self._anchor.winfo_rootx() + self._anchor.winfo_width() - self.winfo_reqwidth()
        y = self._anchor.winfo_rooty() + self._anchor.winfo_height() + 2
        self.geometry(f"+{max(x, 0)}+{y}")

    def _apply(self):
        preset = self._preset.get()
        custom = preset == CUSTOM_RANGE
        self.close()
        self._on_apply(preset, self._from.get() if custom else "", self._to.get() if custom else "")

    def _clear(self):
        self.close()
        self._on_clear()

    def close(self):
        if self.winfo_exists():
            self.destroy()
