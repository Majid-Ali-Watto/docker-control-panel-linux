"""
Popup menu with padding, a border and rounded corners.

A native tk.Menu cannot have either, so this draws one on a RoundedPanel laid over the window.
Entries highlight on hover and run only on a left click (the wheel and other buttons do nothing),
the arrow keys + Enter work, and a click anywhere else or Esc closes it.
"""

import tkinter as tk
from tkinter import ttk

from src.ui.rounded import RoundedPanel, _blend, on_fill, readable, surface_color

_FONT = ("Arial", 10)
_MARGIN = 4          # keep this far from the window edge


class PopupMenu:
    def __init__(self, root):
        self._window = root.winfo_toplevel()
        self._holder = None
        self._entries = []           # (label widget, command) per enabled row, in display order
        self._active = None
        self._pressed = None
        self._colors = None
        self._previous_focus = None
        self._opened_by = None       # serial of the click that opened the menu
        # bind_all, not a window binding: the window already has a <Button-1> binding of its own,
        # and Tk runs only the most specific one per tag
        root.bind_all("<ButtonPress>", self._on_press, add="+")
        root.bind_all("<Escape>", self._on_escape, add="+")

    @property
    def is_open(self):
        return self._holder is not None and self._holder.winfo_exists()

    def _theme(self):
        style = ttk.Style()
        fill = surface_color()
        fg = readable(str(style.lookup("TLabel", "foreground") or "#000000"), fill)
        hover = str(style.lookup("Treeview", "background", ["selected"]) or "#2563eb")
        return {"fill": fill, "fg": fg, "hover": hover, "hover_fg": on_fill(hover, "#ffffff"),
                "border": _blend(fg, fill, 0.35), "muted": readable(_blend(fg, fill, 0.55), fill, 3)}

    def show(self, entries, x_root, y_root, backdrop=None, opened_by=None):
        """Open the menu at a screen position. `entries` holds (label, command, enabled) tuples,
        or None for a separator. `backdrop` is the colour behind the menu (it shows in the
        rounded corners). `opened_by` is the click event that opened it: the window-wide
        "click elsewhere closes the menu" handler also sees that same click, after the handler
        that opened the menu, and must not close it again."""
        self.close()
        self._opened_by = getattr(opened_by, "serial", None)
        window, colors = self._window, self._theme()
        self._colors = colors
        self._previous_focus = window.focus_get()

        holder = self._holder = tk.Frame(window)
        holder.configure(bg=backdrop or colors["fill"])
        panel = RoundedPanel(holder, colors["fill"], radius=10, outline=colors["border"],
                             padding=6, fit_width=True)
        panel.pack()
        body = panel.body
        for entry in entries:
            if entry is None:
                line = tk.Frame(body, height=1)
                line.configure(bg=colors["border"])
                line.pack(fill=tk.X, padx=8, pady=4)
                continue
            label, command, enabled = entry
            row = tk.Label(body, text=label, anchor="w", font=_FONT, padx=14, pady=4)
            row.configure(bg=colors["fill"], fg=colors["fg"] if enabled else colors["muted"])
            row.pack(fill=tk.X)
            if enabled:
                index = len(self._entries)
                row.bind("<Enter>", lambda _e, i=index: self._highlight(i))
                row.bind("<ButtonPress-1>", lambda _e, i=index: setattr(self, "_pressed", i))
                row.bind("<ButtonRelease-1>", lambda _e, i=index: self._release(i))
                self._entries.append((row, command))

        holder.bind("<Up>", lambda _e: self._move(-1))
        holder.bind("<Down>", lambda _e: self._move(1))
        holder.bind("<Return>", lambda _e: self._activate(self._active))
        holder.bind("<space>", lambda _e: self._activate(self._active))
        self._place(x_root, y_root)
        holder.focus_set()

    def _place(self, x_root, y_root):
        window, holder = self._window, self._holder
        window.update_idletasks()
        window.update_idletasks()    # the panel sizes itself from its content in a second pass
        width, height = holder.winfo_reqwidth(), holder.winfo_reqheight()
        x = x_root - window.winfo_rootx()
        y = y_root - window.winfo_rooty()
        x = max(_MARGIN, min(x, window.winfo_width() - width - _MARGIN))
        if y + height > window.winfo_height() - _MARGIN:       # no room below: slide up to fit
            y = max(_MARGIN, window.winfo_height() - height - _MARGIN)
        holder.place(x=x, y=y)
        holder.lift()

    def _highlight(self, index):
        for i, (row, _command) in enumerate(self._entries):
            if i == index:
                row.configure(bg=self._colors["hover"], fg=self._colors["hover_fg"])
            else:
                row.configure(bg=self._colors["fill"], fg=self._colors["fg"])
        self._active = index

    def _move(self, step):
        if self._entries:
            self._highlight(0 if self._active is None else (self._active + step) % len(self._entries))
        return "break"

    def _release(self, index):
        """Left button up on an entry: runs it only if the button also went down on that entry."""
        pressed, self._pressed = self._pressed, None
        if pressed == index:
            self._activate(index)
        return "break"

    def _activate(self, index):
        if index is None or index >= len(self._entries):
            return "break"
        command = self._entries[index][1]
        self.close()
        command()
        return "break"

    def _on_press(self, event):
        if self._opened_by is not None and event.serial == self._opened_by:
            return
        if self.is_open and not str(event.widget).startswith(str(self._holder)):
            self.close()

    def _on_escape(self, _event):
        if self.is_open:
            self.close()
            return "break"

    def close(self):
        holder, self._holder = self._holder, None
        self._entries, self._active, self._pressed = [], None, None
        if holder is None:
            return
        if holder.winfo_exists():
            holder.destroy()
        previous = self._previous_focus
        try:
            if previous is not None and previous.winfo_exists():
                previous.focus_set()
        except tk.TclError:
            pass
