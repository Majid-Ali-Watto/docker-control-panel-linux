"""
Privacy Policy and Terms of Use inside the app: a reader dialog (opened from the Docker home page)
and the agreement shown on first start (and again whenever help/legal.LEGAL_VERSION changes).
The text comes from help/legal.py, the same source as PRIVACY.md and TERMS.md.
"""

import os
import tkinter as tk
from tkinter import ttk

from src.config.config_manager import get_setting, set_setting
from src.help.help_creator import APP_NAME
from src.help.legal import DOCUMENTS, LAST_UPDATED, LEGAL_VERSION
from src.ui.rounded import mix_colors, readable, surface_color

# For unattended setups (kiosks, automated tests): setting this to "yes" counts as accepting
ACCEPT_ENV = "DOCKER_GUI_ACCEPT_TERMS"


def needs_acceptance():
    """True until the current version of the Privacy Policy and Terms has been accepted."""
    if get_setting("legal_accepted") == LEGAL_VERSION:
        return False
    if os.environ.get(ACCEPT_ENV, "").strip().lower() in ("1", "yes", "true", "y"):
        set_setting("legal_accepted", LEGAL_VERSION)
        return False
    return True


def record_acceptance():
    set_setting("legal_accepted", LEGAL_VERSION)


def build_document(parent, kind):
    """A read-only, scrollable, theme-coloured page for DOCUMENTS[kind]; returns its frame."""
    doc = DOCUMENTS[kind]
    frame = ttk.Frame(parent)
    bg = surface_color()
    fg = readable(ttk.Style().lookup("TLabel", "foreground") or "#dddddd", bg)
    muted = readable(mix_colors(fg, bg, 0.4), bg, 3)
    text = tk.Text(frame, wrap=tk.WORD, bg=bg, fg=fg, relief=tk.FLAT, bd=0, highlightthickness=0,
                   padx=18, pady=14, cursor="arrow", spacing1=2, spacing3=4, font=("Arial", 10), height=12,
                   insertwidth=0, takefocus=0)
    bar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
    text.configure(yscrollcommand=bar.set)
    bar.pack(side=tk.RIGHT, fill=tk.Y)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    text.tag_configure("title", font=("Arial", 16, "bold"), spacing3=2)
    text.tag_configure("meta", font=("Arial", 9), foreground=muted, spacing3=10)
    text.tag_configure("intro", spacing3=8)
    text.tag_configure("heading", font=("Arial", 11, "bold"), spacing1=12, spacing3=2)
    text.tag_configure("bullet", lmargin1=16, lmargin2=30)

    text.insert(tk.END, f"{doc['title']}\n", "title")
    text.insert(tk.END, f"{APP_NAME} · last updated {LAST_UPDATED}\n", "meta")
    text.insert(tk.END, doc["intro"] + "\n", "intro")
    for heading, paragraphs in doc["sections"]:
        text.insert(tk.END, heading + "\n", "heading")
        for paragraph in paragraphs:
            if paragraph.startswith("- "):
                text.insert(tk.END, "•  " + paragraph[2:] + "\n", "bullet")
            else:
                text.insert(tk.END, paragraph + "\n")
    text.configure(state=tk.DISABLED)
    frame.text = text
    return frame


def show_legal_dialog(root, kind):
    """Open the Privacy Policy or the Terms of Use (kind: 'privacy' | 'terms') to read."""
    dialog = tk.Toplevel(root)
    dialog.title(f"{DOCUMENTS[kind]['title']} — {APP_NAME}")
    dialog.transient(root)
    dialog.geometry(f"680x560+{max((root.winfo_screenwidth() - 680) // 2, 0)}+"
                    f"{max((root.winfo_screenheight() - 560) // 3, 0)}")
    # bottom widgets are packed first so a small window clips the document, never the buttons
    ttk.Button(dialog, text="Close", style="secondary.TButton", command=dialog.destroy,
               width=12).pack(side=tk.BOTTOM, pady=10)
    build_document(dialog, kind).pack(fill=tk.BOTH, expand=True)
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    dialog.focus_set()
    return dialog


def _grab_when_viewable(dialog, tries=40):
    """Make the dialog modal. Tk refuses a grab on a window that is not on screen yet ("grab failed:
    window not viewable"), which a busy machine makes likely: retry shortly instead of crashing."""
    try:
        dialog.grab_set()
    except tk.TclError:
        if tries and dialog.winfo_exists():
            dialog.after(50, lambda: _grab_when_viewable(dialog, tries - 1))


def ask_first_run(root):
    """The agreement shown on first start. True when the user accepts (and it is recorded)."""
    dialog = tk.Toplevel(root)
    dialog.title(f"Welcome to {APP_NAME}")
    dialog.transient(root)
    dialog.geometry(f"700x620+{max((root.winfo_screenwidth() - 700) // 2, 0)}+"
                    f"{max((root.winfo_screenheight() - 620) // 4, 0)}")
    _grab_when_viewable(dialog)
    result = {"accepted": False}

    ttk.Label(dialog, text=f"Welcome to {APP_NAME}", font=("Arial", 14, "bold")).pack(pady=(16, 2))
    ttk.Label(dialog, text="Please read the Privacy Policy and the Terms of Use, then accept to continue.",
              style="Muted.TLabel", font=("Arial", 9)).pack(pady=(0, 8))

    # Buttons and checkbox first (bottom), then the documents take whatever room is left, so a small
    # window clips the text and never the Accept / Decline buttons
    buttons = ttk.Frame(dialog)
    buttons.pack(side=tk.BOTTOM, fill=tk.X, padx=18, pady=(4, 14))
    agree = tk.BooleanVar(master=dialog, value=False)
    ttk.Checkbutton(dialog, variable=agree, text="I have read and agree to the Privacy Policy and the "
                    "Terms of Use").pack(side=tk.BOTTOM, anchor=tk.W, padx=18, pady=(10, 4))
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=14)
    for kind, doc in DOCUMENTS.items():
        notebook.add(build_document(notebook, kind), text=f"  {doc['title']}  ")

    def accept():
        record_acceptance()
        result["accepted"] = True
        dialog.destroy()

    accept_button = ttk.Button(buttons, text="Accept and continue", style="success.TButton",
                               command=accept, state=tk.DISABLED)
    accept_button.pack(side=tk.RIGHT)
    ttk.Button(buttons, text="Decline and exit", style="secondary.TButton",
               command=dialog.destroy).pack(side=tk.RIGHT, padx=(0, 8))
    agree.trace_add("write", lambda *_: accept_button.configure(state=tk.NORMAL if agree.get() else tk.DISABLED))
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)       # closing the window is declining
    dialog.focus_set()
    dialog.wait_window()
    return result["accepted"]
