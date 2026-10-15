"""
Landing page of the Docker category: a hero banner with the service status, quick service
buttons and one card per sidebar category (click a card to open it).
"""

import tkinter as tk
from tkinter import ttk

from src.ui.rounded import RoundedPanel, make
from src.ui.scroll_frame import ScrollFrame

HERO_BG, HERO_TITLE, HERO_TEXT = "#0d1117", "#4ea8f7", "#8a9fb5"
_CARD_MIN_WIDTH = 230

# (category, icon, one-line description)
_CARDS = [
    ("Containers", "📦", "List, start, stop, inspect and open a shell or logs for your containers."),
    ("Images", "🖼", "Pull, search Docker Hub, build, load, tag and clean up images."),
    ("Volumes", "💾", "Create, inspect and prune the volumes that hold your data."),
    ("Networks", "🕸", "Create and inspect networks, connect containers to them."),
    ("Compose", "🧩", "Bring Compose projects up and down from files or folders."),
    ("Stats", "📊", "Live CPU, memory and I/O per container, plus disk usage."),
    ("Terminal", "🖥", "A built-in shell for quick commands, without leaving the app."),
]

# Service buttons keep the sidebar's names; value is the button style
_SERVICE_STYLES = {"Start": "success.TButton", "Stop": "warning.TButton",
                   "Restart": "info.TButton", "Clean All": "danger.Outline.TButton"}


class LandingPage(ttk.Frame):
    def __init__(self, parent, status_var, service_actions, open_category, available):
        """service_actions: [(label, callback)]; open_category(name) opens a sidebar category;
        available: the category names that exist in the sidebar."""
        super().__init__(parent)
        self._open = open_category
        self.scroller = ScrollFrame(self, pad=4)
        self.scroller.pack(fill=tk.BOTH, expand=True)
        body = self.scroller.body

        self._build_hero(body, status_var)
        self._build_service(body, service_actions)
        ttk.Label(body, text="Explore", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(16, 6))
        self.card_grid = ttk.Frame(body)
        self.card_grid.pack(fill=tk.X)
        self._available = set(available)
        self._cards, self._columns = [], 0
        self.scroller.canvas.bind("<Configure>", self._relayout, add="+")
        self._tips(body)
        # the cards are the bulk of the widgets: build them once the window has painted
        self.after_idle(self.after, 1, self._build_cards)

    def _build_cards(self):
        if not self.winfo_exists():
            return
        self._cards = [self._card(self.card_grid, *card) for card in _CARDS if card[0] in self._available]
        self._relayout(width=self.scroller.canvas.winfo_width())

    def _build_hero(self, parent, status_var):
        hero = RoundedPanel(parent, HERO_BG, radius=14, padding=2)
        hero.pack(fill=tk.X, pady=(2, 0))
        body = hero.body
        make(tk.Label, body, text="🐳", font=("Arial", 34), bg=HERO_BG, fg=HERO_TITLE).pack(side=tk.LEFT, padx=(20, 14), pady=16)
        text = make(tk.Frame, body, bg=HERO_BG)
        text.pack(side=tk.LEFT, pady=16)
        make(tk.Label, text, text="Docker Control Panel", font=("JetBrains Mono", 16, "bold"),
             bg=HERO_BG, fg=HERO_TITLE).pack(anchor=tk.W)
        make(tk.Label, text, text="A graphical Docker manager for Linux", font=("Arial", 10),
             bg=HERO_BG, fg=HERO_TEXT).pack(anchor=tk.W, pady=(2, 8))
        status = make(tk.Label, text, font=("Arial", 9, "bold"), bg="#1b2733", fg="#c0d8f0", padx=10, pady=3)
        status.configure(textvariable=status_var)
        status.pack(anchor=tk.W)

    def _build_service(self, parent, service_actions):
        frame = ttk.LabelFrame(parent, text="Docker service", padding=(12, 8))
        frame.pack(fill=tk.X, pady=(14, 0))
        for label, callback in service_actions:
            ttk.Button(frame, text=label, style=_SERVICE_STYLES.get(label, "secondary.TButton"),
                       command=callback, width=11).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(frame, text="Needs sudo — the saved password is used.", style="secondary.TLabel",
                  font=("Arial", 8)).pack(side=tk.RIGHT)

    def _card(self, parent, category, icon, description):
        card = ttk.LabelFrame(parent, padding=(14, 12))
        head = ttk.Frame(card)
        head.pack(fill=tk.X)
        ttk.Label(head, text=icon, font=("Arial", 20)).pack(side=tk.LEFT)
        ttk.Label(head, text=category, font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(10, 0))
        desc = ttk.Label(card, text=description, font=("Arial", 9), justify=tk.LEFT, anchor=tk.W)
        desc.pack(fill=tk.X, pady=(8, 8))
        ttk.Button(card, text="Open  →", style="secondary.Outline.TButton",
                   command=lambda: self._open(category)).pack(anchor=tk.W)
        card.description = desc
        for widget in (card, head, desc, *head.winfo_children()):
            widget.bind("<Button-1>", lambda _e, c=category: self._open(c))
            widget.configure(cursor="hand2")
        return card

    def _relayout(self, event=None, width=None):
        """As many cards per row as fit; descriptions wrap to the card width."""
        width = width if width is not None else event.width
        columns = max(1, min(4, width // _CARD_MIN_WIDTH))
        if columns == self._columns or not self._cards:
            return
        self._columns = columns
        for index, card in enumerate(self._cards):
            card.grid(row=index // columns, column=index % columns, padx=5, pady=5, sticky="nsew")
            card.description.configure(wraplength=max(width // columns - 70, 120))
        for column in range(4):
            used = column < columns
            self.card_grid.columnconfigure(column, weight=1 if used else 0, uniform="card" if used else "")

    def _tips(self, parent):
        ttk.Label(parent, text="Tips", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(16, 4))
        for tip in ("Select a row in a table, then use the action buttons below it.",
                    "Right-click a row for a menu; double-click it for details.",
                    "The panel on the right has the Commands reference and Help."):
            ttk.Label(parent, text=f"•  {tip}", font=("Arial", 9), anchor=tk.W).pack(fill=tk.X, pady=1)
