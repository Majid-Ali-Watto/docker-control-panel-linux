"""
Creator tab: a profile card (avatar, name, role), link cards with Open / Copy, and an
"About the app" card with the tech stack as chips.
"""

import tkinter as tk
from tkinter import ttk

from src.help.help_creator import (
    APP_BUILT_WITH, APP_NAME, APP_REQUIRES, APP_TAGLINE,
    CREATOR_GITHUB_LABEL, CREATOR_GITHUB_URL, CREATOR_NAME,
    CREATOR_PORTFOLIO_LABEL, CREATOR_PORTFOLIO_URL, CREATOR_ROLE,
)
from src.ui.rounded import RoundedBadge, RoundedPanel, make
from src.ui.scroll_frame import ScrollFrame

_BG, _NAME, _ROLE, _AVATAR = "#0d1117", "#e6edf3", "#8a9fb5", "#2563eb"
_LINKS = [("🌐", "Portfolio", CREATOR_PORTFOLIO_LABEL, CREATOR_PORTFOLIO_URL),
          ("🐙", "GitHub", CREATOR_GITHUB_LABEL, CREATOR_GITHUB_URL)]


def _initials(name):
    return "".join(part[0] for part in name.split()[:2]).upper()


def _profile(parent):
    panel = RoundedPanel(parent, _BG, radius=14, padding=2)
    panel.pack(fill=tk.X, pady=(2, 0))
    body = panel.body
    avatar = tk.Canvas(body, width=76, height=76, bg=_BG, highlightthickness=0, bd=0)
    avatar.create_oval(2, 2, 74, 74, fill=_AVATAR, outline="")
    avatar.create_text(38, 38, text=_initials(CREATOR_NAME), fill="#ffffff", font=("Arial", 22, "bold"))
    avatar.pack(side=tk.LEFT, padx=(20, 16), pady=18)
    text = make(tk.Frame, body, bg=_BG)
    text.pack(side=tk.LEFT, pady=18)
    make(tk.Label, text, text=CREATOR_NAME, font=("Arial", 16, "bold"), bg=_BG, fg=_NAME).pack(anchor=tk.W)
    make(tk.Label, text, text=CREATOR_ROLE, font=("Arial", 10), bg=_BG, fg=_ROLE).pack(anchor=tk.W, pady=(2, 0))


def _link_card(parent, icon, label, text, url, open_link):
    card = ttk.LabelFrame(parent, padding=(12, 10))
    card.pack(fill=tk.X, pady=4)
    ttk.Label(card, text=icon, font=("Arial", 18)).grid(row=0, column=0, rowspan=2, padx=(0, 12))
    ttk.Label(card, text=label, font=("Arial", 11, "bold")).grid(row=0, column=1, sticky="w")
    ttk.Label(card, text=text, font=("JetBrains Mono", 9), style="Muted.TLabel").grid(row=1, column=1, sticky="w")
    card.columnconfigure(1, weight=1)
    copy = ttk.Button(card, text="Copy", width=7, style="secondary.TButton")
    copy.grid(row=0, column=2, rowspan=2, padx=(8, 6))

    def copy_url():
        card.clipboard_clear()
        card.clipboard_append(url)
        copy.configure(text="✓ Copied")
        copy.after(1200, lambda: copy.winfo_exists() and copy.configure(text="Copy"))

    copy.configure(command=copy_url)
    ttk.Button(card, text="Open ↗", width=8, style="primary.TButton",
               command=lambda: open_link(url)).grid(row=0, column=3, rowspan=2)


def _about(parent):
    card = ttk.LabelFrame(parent, padding=(14, 12))
    card.pack(fill=tk.X, pady=4)
    ttk.Label(card, text=f"🐳  {APP_NAME}", font=("Arial", 12, "bold")).pack(anchor=tk.W)
    ttk.Label(card, text=APP_TAGLINE, font=("Arial", 9), style="Muted.TLabel").pack(anchor=tk.W, pady=(2, 10))
    ttk.Label(card, text="BUILT WITH", font=("Arial", 8, "bold"), style="Muted.TLabel").pack(anchor=tk.W)
    chips = ttk.Frame(card)
    chips.pack(anchor=tk.W, pady=(4, 10))
    for tech in APP_BUILT_WITH.split(" · "):
        RoundedBadge(chips, text=tech, fill="#1a4a6b", fg="#c0d8f0").pack(side=tk.LEFT, padx=(0, 6))
    ttk.Label(card, text="REQUIRES", font=("Arial", 8, "bold"), style="Muted.TLabel").pack(anchor=tk.W)
    ttk.Label(card, text=APP_REQUIRES, font=("Arial", 10)).pack(anchor=tk.W, pady=(2, 0))


def build_creator_tab(notebook, open_link):
    """Add the Creator tab to `notebook`; open_link(url) opens a URL in the browser."""
    scroller = ScrollFrame(notebook, pad=10)
    notebook.add(scroller, text=" Creator ")
    body = scroller.body
    _profile(body)
    ttk.Label(body, text="Links", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(16, 4))
    for icon, label, text, url in _LINKS:
        _link_card(body, icon, label, text, url, open_link)
    ttk.Label(body, text="About", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(16, 4))
    _about(body)
    return scroller
