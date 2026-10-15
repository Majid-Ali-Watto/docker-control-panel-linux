"""
Help tab: searchable, collapsible topic cards built from help_info.HELP_SECTIONS.

Each card shows an icon, a title and a one-line summary; clicking it expands the content.
Typing in the search box shows only matching cards (expanded). "Expand all" / "Collapse all"
sit next to it. The first card starts open.
"""

import tkinter as tk
from tkinter import ttk

from src.help.help_info import HELP_SECTIONS
from src.ui.scroll_frame import ScrollFrame

_CARD_STYLE = "HelpCard.secondary.TButton"   # left-aligned card header
_INDENT = 34        # content is indented under the card title


class _Card(ttk.Frame):
    def __init__(self, parent, scroller, icon, title, summary, blocks):
        super().__init__(parent, padding=(0, 3))
        self.title = title
        self.open = False
        self.search_text = " ".join([title, summary] + [self._flat(b) for b in blocks]).lower()

        self.header = ttk.Button(self, style=_CARD_STYLE, command=self.toggle, cursor="hand2")
        self.header.pack(fill=tk.X)
        self._label = (icon, title, summary)
        self.body = ttk.Frame(self, padding=(_INDENT, 8, 8, 6))
        for block in blocks:
            self._render(scroller, block)
        self._refresh_header()

    @staticmethod
    def _flat(block):
        kind, data = block
        if kind in ("p",):
            return data
        if kind in ("steps", "list"):
            return " ".join(data)
        return " ".join(f"{a} {b}" for a, b in data)

    def toggle(self):
        self.set_open(not self.open)

    def set_open(self, value):
        self.open = value
        if value:
            self.body.pack(fill=tk.X)
        else:
            self.body.pack_forget()
        self._refresh_header()

    def _refresh_header(self):
        icon, title, summary = self._label
        arrow = "▾" if self.open else "▸"
        self.header.configure(text=f" {arrow}  {icon}  {title}   —   {summary}")

    # ---- block renderers ----------------------------------------------------------------
    def _render(self, scroller, block):
        kind, data = block
        getattr(self, f"_{kind}")(scroller, data)

    def _p(self, scroller, text):
        scroller.wrap(ttk.Label(self.body, text=text, font=("Arial", 10), justify=tk.LEFT, anchor=tk.W),
                      _INDENT + 70).pack(fill=tk.X, pady=3)

    def _numbered(self, scroller, items, bullets):
        for index, text in enumerate(items, 1):
            row = ttk.Frame(self.body)
            row.pack(fill=tk.X, pady=3)
            marker = "•" if bullets else str(index)
            ttk.Label(row, text=marker, font=("Arial", 10, "bold"), width=2, anchor="n").pack(side=tk.LEFT, anchor="n")
            scroller.wrap(ttk.Label(row, text=text, font=("Arial", 10), justify=tk.LEFT, anchor=tk.W),
                          _INDENT + 100).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _steps(self, scroller, items):
        self._numbered(scroller, items, bullets=False)

    def _list(self, scroller, items):
        self._numbered(scroller, items, bullets=True)

    def _kv(self, scroller, rows):
        for term, text in rows:
            row = ttk.Frame(self.body)
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=term, font=("Arial", 10, "bold"), anchor=tk.W).pack(fill=tk.X)
            scroller.wrap(ttk.Label(row, text=text, font=("Arial", 9), justify=tk.LEFT, anchor=tk.W),
                          _INDENT + 70).pack(fill=tk.X, padx=(14, 0))

    def _keys(self, scroller, rows):
        grid = ttk.Frame(self.body)
        grid.pack(fill=tk.X, pady=2)
        grid.columnconfigure(1, weight=1)
        for index, (keys, text) in enumerate(rows):
            caps = ttk.Frame(grid)
            caps.grid(row=index, column=0, sticky="w", padx=(0, 12), pady=3)
            for number, key in enumerate(keys.split("+")):
                if number:
                    ttk.Label(caps, text="+", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
                ttk.Label(caps, text=key, font=("JetBrains Mono", 9, "bold"), padding=(7, 2),
                          relief="solid", borderwidth=1, anchor="center").pack(side=tk.LEFT)
            scroller.wrap(ttk.Label(grid, text=text, font=("Arial", 10), justify=tk.LEFT, anchor=tk.W),
                          _INDENT + 150).grid(row=index, column=1, sticky="w")


class HelpTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Style().configure(_CARD_STYLE, anchor="w", padding=(10, 8))
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(bar, text="🔍").pack(side=tk.LEFT, padx=(2, 4))
        self.query = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.query)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=2)
        entry.bind("<Escape>", lambda _e: self.query.set(""))
        ttk.Button(bar, text="Expand all", style="secondary.TButton",
                   command=lambda: self._set_all(True)).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="Collapse all", style="secondary.TButton",
                   command=lambda: self._set_all(False)).pack(side=tk.LEFT)

        self.scroller = ScrollFrame(self, pad=8)
        self.scroller.pack(fill=tk.BOTH, expand=True)
        self.cards = []
        self.empty = ttk.Label(self.scroller.body, text="Nothing in Help matches your search.", font=("Arial", 10))
        self._saved_open = None
        self.query.trace_add("write", lambda *_: self._on_search())
        self.bind("<Map>", self._build_once)    # the cards are only created when the tab is first shown

    def _build_once(self, _event=None):
        if self.cards:
            return
        self.cards = [_Card(self.scroller.body, self.scroller, *section) for section in HELP_SECTIONS]
        self.cards[0].set_open(True)
        self._layout(bool(self.query.get().strip()))

    def _set_all(self, value):
        self._build_once()
        for card in self.cards:
            card.set_open(value)

    def _layout(self, filtering):
        needle = self.query.get().strip().lower().split()
        shown = 0
        for card in self.cards:
            card.pack_forget()
            if all(word in card.search_text for word in needle):
                card.pack(fill=tk.X)
                shown += 1
                if filtering:
                    card.set_open(True)
        self.empty.pack_forget()
        if not shown:
            self.empty.pack(pady=30)

    def _on_search(self):
        self._build_once()
        filtering = bool(self.query.get().strip())
        if filtering and self._saved_open is None:       # remember the layout to restore it later
            self._saved_open = [card.open for card in self.cards]
        self._layout(filtering)
        if not filtering and self._saved_open is not None:
            for card, was_open in zip(self.cards, self._saved_open):
                card.set_open(was_open)
            self._saved_open = None
        self.scroller.scroll_to_top()


def build_help_tab(notebook):
    """Add the Help tab to `notebook`."""
    tab = HelpTab(notebook)
    notebook.add(tab, text=" Help ")
    return tab
