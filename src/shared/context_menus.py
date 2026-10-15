"""
Context menu setup and clipboard utilities for table and text widgets.
"""

import tkinter as tk

from src.ui.popup_menu import PopupMenu


def setup_text_context_menu(text_widget, root):
    """Setup right-click context menu for text widget"""
    def show_context_menu(event):
        context_menu = tk.Menu(root, tearoff=0)
        context_menu.add_command(label="Copy", command=lambda: text_widget.event_generate("<<Copy>>"))
        context_menu.add_command(label="Select All", command=lambda: text_widget.tag_add(tk.SEL, "1.0", tk.END))
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    text_widget.bind("<Button-3>", show_context_menu)


def setup_table_context_menu(display_manager, root):
    """Right-click menu and Ctrl+C for the main table.

    Right-click selects the cell under the pointer (and its row, unless it is already part of
    the selection) so the menu always acts on what was clicked: copy the cell, copy the
    selected rows, select all rows, then the same row actions the toolbar offers.
    """
    table = display_manager.table_widget
    cells = display_manager.cells

    def copy_cell():
        cell = cells.value()
        if cell is None:
            return False
        column, text = cell
        copy_to_clipboard(root, text)
        display_manager.set_status(f"Copied {column}: {text}" if text else f"Copied empty {column}")
        return True

    def copy_rows():
        count = len(table.selection())
        copy_to_clipboard(root, display_manager.selected_rows_text())
        display_manager.set_status(f"Copied {count} row{'s' if count != 1 else ''}")

    def select_all(_event=None):
        display_manager.select_all_rows()
        return "break"

    def on_copy_key(_event):
        if not copy_cell() and table.selection():
            copy_rows()
        return "break"

    menu = PopupMenu(root)

    def show_context_menu(event):
        """Right button down: make the clicked cell (and its row, unless already selected) the
        active one, then open the menu with copy, select-all and the toolbar's row actions."""
        row = table.identify_row(event.y)
        if not row or table.identify_region(event.x, event.y) != "cell":
            return
        if row not in table.selection():
            table.selection_set(row)
            display_manager.update_selection_state()   # the menu reads the buttons' enabled state
        cells.at(event.x, event.y)
        column, text = cells.value()

        shown = text if len(text) <= 30 else text[:30] + "..."
        count = len(table.selection())
        entries = [
            (f"Copy {column}: {shown}" if text else f"Copy {column} (empty)", copy_cell, True),
            ("Copy Selected Row" + ("s" if count != 1 else ""), copy_rows, True),
            ("Select All Rows (Ctrl+A)", select_all, True),
        ]
        actions = display_manager.row_actions()
        if actions:
            entries += [None] + actions
        entries += [None, ("Close menu", menu.close, True)]

        tags = table.item(row, "tags")
        backdrop = (table.tag_configure(tags[0], "background") or None) if tags else None
        menu.show(entries, event.x_root, event.y_root, backdrop, opened_by=event)

    table.bind("<ButtonPress-3>", show_context_menu)
    table.bind("<Control-a>", select_all)
    table.bind("<Control-A>", select_all)
    table.bind("<Control-c>", on_copy_key)
    table.bind("<Control-C>", on_copy_key)


def copy_to_clipboard(root, text):
    """Copy text to clipboard"""
    root.clipboard_clear()
    root.clipboard_append(str(text))
