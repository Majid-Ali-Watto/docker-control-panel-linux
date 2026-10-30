"""
Landing page of the Docker category: a hero banner with the service status, quick service
buttons (with tooltips), a live "How it works" card (which CLI / engine / socket is in use) and one
card per sidebar category (click a card to open it).
"""

import base64
import io
import os
import tkinter as tk
from tkinter import ttk

from PIL import Image

from src.help.help_creator import CREATOR_EMAIL, CREATOR_NAME
from src.system.overview import gather_overview
from src.ui.rounded import RoundedPanel, make
from src.ui.scroll_frame import ScrollFrame
from src.ui.ui_components import Tooltip
from src.ui.workflow_view import WorkflowDiagram

ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "assets", "docker-icon.png")
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

_LEGAL_LINKS = [("privacy", "Privacy Policy"), ("terms", "Terms of Use")]
_LEGAL_TIPS = {"privacy": "What the app stores on your computer and when it uses the network",
               "terms": "The terms for using Docker Control Panel"}

# Service buttons keep the sidebar's names; value is the button style
_SERVICE_STYLES = {"Start": "success.TButton", "Stop": "warning.TButton",
                   "Restart": "info.TButton", "Clean All": "danger.Outline.TButton"}


class LandingPage(ttk.Frame):
    def __init__(self, parent, status_var, service_actions, open_category, available,
                 button_tips=None, category_tips=None, fetch_overview=gather_overview, open_legal=None):
        """service_actions: [(label, callback)]; open_category(name) opens a sidebar category;
        available: the category names that exist in the sidebar; button_tips / category_tips:
        tooltip text per service button / per category; fetch_overview() -> dict for the live card;
        open_legal(kind) shows the Privacy Policy ('privacy') or Terms of Use ('terms')."""
        super().__init__(parent)
        self._open = open_category
        self._button_tips = button_tips or {}
        self._category_tips = category_tips or {}
        self._open_legal = open_legal
        self.scroller = ScrollFrame(self, pad=4)
        self.scroller.pack(fill=tk.BOTH, expand=True)
        body = self.scroller.body

        self._build_hero(body, status_var)
        self._build_service(body, service_actions)
        self.workflow = WorkflowDiagram(body, fetch_overview)
        self.workflow.pack(fill=tk.X, pady=(14, 0))
        # look again whenever the page is shown and whenever the Docker status is re-read (after
        # Start / Stop / Restart, or once the password has been entered)
        self.bind("<Map>", lambda e: e.widget is self and self.workflow.refresh(), add="+")
        status_var.trace_add("write", lambda *_: self.after(400, self._refresh_if_visible))
        ttk.Label(body, text="Explore", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(16, 6))
        self.card_grid = ttk.Frame(body)
        self.card_grid.pack(fill=tk.X)
        self._available = set(available)
        self._cards, self._columns = [], 0
        self.scroller.canvas.bind("<Configure>", self._relayout, add="+")
        self._tips(body)
        self._footer(body)
        # the cards are the bulk of the widgets: build them once the window has painted
        self.after_idle(self.after, 1, self._build_cards)

    def _refresh_if_visible(self):
        if self.winfo_exists() and self.winfo_ismapped():
            self.workflow.refresh()

    def _build_cards(self):
        if not self.winfo_exists():
            return
        self._cards = [self._card(self.card_grid, *card) for card in _CARDS if card[0] in self._available]
        self._relayout(width=self.scroller.canvas.winfo_width())

    def _build_hero(self, parent, status_var):
        hero = RoundedPanel(parent, HERO_BG, radius=14, padding=2)
        hero.pack(fill=tk.X, pady=(2, 0))
        body = hero.body
        self._hero_icon(body).pack(side=tk.LEFT, padx=(20, 14), pady=16)
        text = make(tk.Frame, body, bg=HERO_BG)
        text.pack(side=tk.LEFT, pady=16)
        make(tk.Label, text, text="Docker Control Panel", font=("JetBrains Mono", 16, "bold"),
             bg=HERO_BG, fg=HERO_TITLE).pack(anchor=tk.W)
        make(tk.Label, text, text="A graphical Docker manager for Linux", font=("Arial", 10),
             bg=HERO_BG, fg=HERO_TEXT).pack(anchor=tk.W, pady=(2, 8))
        status = make(tk.Label, text, font=("Arial", 9, "bold"), bg="#1b2733", fg="#c0d8f0", padx=10, pady=3)
        status.configure(textvariable=status_var)
        status.pack(anchor=tk.W)
        links = make(tk.Frame, body, bg=HERO_BG)
        links.pack(side=tk.RIGHT, anchor=tk.N, padx=18, pady=14)
        for kind, label in _LEGAL_LINKS:
            link = make(tk.Label, links, text=label, font=("Arial", 9, "underline"), bg=HERO_BG, fg=HERO_TEXT,
                        cursor="hand2")
            link.pack(anchor=tk.E, pady=1)
            self._wire_legal(link, kind)

    def _hero_icon(self, parent):
        """The app icon at 72 px; the whale emoji if the image cannot be loaded."""
        try:
            resample = getattr(Image, "Resampling", Image).LANCZOS
            picture = Image.open(ICON_PATH).convert("RGBA").resize((72, 72), resample)
            data = io.BytesIO()
            picture.save(data, "PNG")
            self._icon = tk.PhotoImage(data=base64.b64encode(data.getvalue()))    # keep a reference
            return make(tk.Label, parent, image=self._icon, bg=HERO_BG)
        except Exception:
            return make(tk.Label, parent, text="🐳", font=("Arial", 34), bg=HERO_BG, fg=HERO_TITLE)

    def _wire_legal(self, widget, kind):
        """Make `widget` open a legal page on click, with a tooltip."""
        widget.bind("<Button-1>", lambda _e: self._open_legal and self._open_legal(kind))
        Tooltip(widget, _LEGAL_TIPS[kind])

    def _footer(self, parent):
        footer = ttk.Frame(parent)
        footer.pack(fill=tk.X, pady=(18, 6))
        ttk.Separator(footer).pack(fill=tk.X, pady=(0, 8))
        for kind, label in _LEGAL_LINKS:
            link = ttk.Label(footer, text=label, font=("Arial", 9, "underline"), cursor="hand2")
            link.pack(side=tk.LEFT, padx=(0, 14))
            self._wire_legal(link, kind)
        ttk.Label(footer, text=f"© 2026 {CREATOR_NAME} · {CREATOR_EMAIL}", style="Muted.TLabel",
                  font=("Arial", 8)).pack(side=tk.RIGHT)

    def _build_service(self, parent, service_actions):
        frame = ttk.LabelFrame(parent, text="Docker service", padding=(12, 8))
        frame.pack(fill=tk.X, pady=(14, 0))
        for label, callback in service_actions:
            button = ttk.Button(frame, text=label, style=_SERVICE_STYLES.get(label, "secondary.TButton"),
                                command=callback, width=11)
            button.pack(side=tk.LEFT, padx=(0, 8))
            if label in self._button_tips:
                Tooltip(button, self._button_tips[label])
        ttk.Label(frame, text="Needs sudo — the saved password is used.", style="Muted.TLabel",
                  font=("Arial", 8)).pack(side=tk.RIGHT)

    def _card(self, parent, category, icon, description):
        card = ttk.LabelFrame(parent, padding=(14, 12))
        head = ttk.Frame(card)
        head.pack(fill=tk.X)
        ttk.Label(head, text=icon, font=("Arial", 20)).pack(side=tk.LEFT)
        ttk.Label(head, text=category, font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(10, 0))
        desc = ttk.Label(card, text=description, font=("Arial", 9), justify=tk.LEFT, anchor=tk.W)
        desc.pack(fill=tk.X, pady=(8, 8))
        open_button = ttk.Button(card, text="Open  →", style="secondary.TButton",
                                 command=lambda: self._open(category))
        open_button.pack(anchor=tk.W)
        card.description = desc
        tip = self._category_tips.get(category)
        for widget in (card, head, desc, *head.winfo_children()):
            widget.bind("<Button-1>", lambda _e, c=category: self._open(c))
            widget.configure(cursor="hand2")
            if tip:
                Tooltip(widget, tip)
        if tip:
            Tooltip(open_button, tip)
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
