"""
ScrollFrame: a vertically scrolling container for ordinary widgets.

Put content in ``.body``. Mouse wheel scrolls while the pointer is over it, the inner width
follows the canvas, and labels registered with ``wrap()`` re-wrap to the available width.
The canvas colour follows the ttk theme (``<<ThemeChanged>>``).
"""

import tkinter as tk
from tkinter import ttk

from src.ui.rounded import surface_color


class ScrollFrame(ttk.Frame):
    def __init__(self, parent, pad=0):
        super().__init__(parent)
        self._pad = pad
        self._wrapped = []
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=surface_color())
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.body = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<<ThemeChanged>>", lambda _e: self.canvas.configure(bg=surface_color()))
        for widget in (self.canvas, self.body):
            widget.bind("<Enter>", self._bind_wheel)
            widget.bind("<Leave>", self._unbind_wheel)

    def wrap(self, label, margin=0):
        """Keep `label` wrapped to the scroll area's width minus `margin` pixels."""
        self._wrapped.append((label, margin))
        return label

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)

    def _on_body(self, _event):
        self.canvas.configure(scrollregion=(0, 0, self.body.winfo_reqwidth(), self.body.winfo_reqheight()))

    def _on_canvas(self, event):
        width = max(event.width - 2 * self._pad, 1)
        self.canvas.itemconfigure(self._window, width=width)
        self.canvas.coords(self._window, self._pad, 0)
        self._wrapped[:] = [(w, m) for w, m in self._wrapped if w.winfo_exists()]
        for label, margin in self._wrapped:
            label.configure(wraplength=max(width - margin, 40))

    # wheel events go to the focused/hovered widget, so listen app-wide only while hovering
    def _bind_wheel(self, _event):
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.bind_all("<Button-4>", self._on_wheel)
        self.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self, _event):
        # moving onto a child still counts as "inside"
        x, y = self.winfo_pointerxy()
        if self.winfo_containing(x, y) is not None and str(self.winfo_containing(x, y)).startswith(str(self)):
            return
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(sequence)

    def _on_wheel(self, event):
        if self.body.winfo_reqheight() <= self.canvas.winfo_height():
            return
        step = -1 if event.num == 4 or getattr(event, "delta", 0) > 0 else 1
        self.canvas.yview_scroll(step * 3, "units")
