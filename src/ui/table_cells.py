"""
Cell selection for the main table.

A Treeview only selects whole rows. CellSelection remembers which cell was clicked, outlines it
(four thin frames laid over the cell) and hands back its raw text for copying. The outline only
shows while the cell's row is selected, so it can never point at a deselected row.
"""

import tkinter as tk
from tkinter import ttk

_EDGE = 2


class CellSelection:
    def __init__(self, tree, row_texts):
        """``row_texts(iid)`` returns the row as the user reads it (index first); empty cells are ''."""
        self.tree = tree
        self._row_texts = row_texts
        self.iid = None
        self.col = None              # Treeview column id such as "#3"
        self._edges = [tk.Frame(tree) for _ in range(4)]
        tree.bind("<ButtonRelease-1>", self._on_release, add="+")
        tree.bind("<<TreeviewSelect>>", self.refresh, add="+")
        # The scroll callbacks fire after every layout change (scroll, resize, reload)
        for option in ("yscrollcommand", "xscrollcommand"):
            self._wrap_scroll(option)

    def _wrap_scroll(self, option):
        original = str(self.tree.cget(option))

        def scrolled(*args):
            if original:
                self.tree.tk.call(original, *args)
            self.refresh()
        self.tree.configure(**{option: scrolled})

    def _on_release(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell":
            self.iid, self.col = self.tree.identify_row(event.y), self.tree.identify_column(event.x)
        self.refresh()               # also follows a column resize, which moves the cell

    def at(self, x, y):
        """Make the cell under (x, y) the active one; False when the point is not on a cell."""
        if self.tree.identify_region(x, y) != "cell":
            return False
        self.iid, self.col = self.tree.identify_row(y), self.tree.identify_column(x)
        self.refresh()
        return True

    def move_to_row(self, iid):
        """Keep the active column but follow the row to its new id (None clears the cell)."""
        self.iid = iid
        if iid is None:
            self.col = None
        self.refresh()

    def clear(self):
        self.move_to_row(None)

    def value(self):
        """(column name, text) of the active cell, '' for an empty one; None without a cell."""
        if self.iid is None or self.col is None:
            return None
        values, index = self._row_texts(self.iid), int(self.col[1:]) - 1
        if not 0 <= index < len(values):
            return None
        return self.tree["columns"][index], str(values[index])

    def refresh(self, _event=None):
        box = None
        if self.iid is not None and self.col is not None and self.iid in self.tree.selection():
            box = self.tree.bbox(self.iid, self.col) or None
        if not box:
            for edge in self._edges:
                edge.place_forget()
            return
        x, y, w, h = box
        # Selected text colour: the one colour guaranteed to contrast with the selected row
        color = ttk.Style().lookup("Treeview", "foreground", ["selected"]) or "white"
        places = ((x, y, w, _EDGE), (x, y + h - _EDGE, w, _EDGE),
                  (x, y, _EDGE, h), (x + w - _EDGE, y, _EDGE, h))
        for edge, (ex, ey, ew, eh) in zip(self._edges, places):
            edge.configure(bg=color)
            edge.place(x=ex, y=ey, width=ew, height=eh)
            edge.lift()
