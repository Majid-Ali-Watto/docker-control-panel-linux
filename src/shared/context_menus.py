"""
Context menu setup and clipboard utilities for table and text widgets.
"""

import tkinter as tk


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


def setup_table_context_menu(table_widget, root):
    """Setup right-click context menu for table widget"""
    def show_context_menu(event):
        selection = table_widget.selection()
        if not selection:
            return

        item = table_widget.selection()[0]
        values = table_widget.item(item)["values"]
        columns = table_widget["columns"]

        context_menu = tk.Menu(root, tearoff=0)

        for i, col in enumerate(columns):
            if i < len(values):
                value = str(values[i])
                display_value = value[:30] + "..." if len(value) > 30 else value
                context_menu.add_command(
                    label=f"Copy {col}: {display_value}",
                    command=lambda v=value: copy_to_clipboard(root, v)
                )

        context_menu.add_separator()
        context_menu.add_command(label="Copy All Selected Rows",
                               command=lambda: copy_table_rows(root, table_widget))

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    table_widget.bind("<Button-3>", show_context_menu)


def copy_to_clipboard(root, text):
    """Copy text to clipboard"""
    root.clipboard_clear()
    root.clipboard_append(str(text))


def copy_table_rows(root, table_widget):
    """Copy selected table rows to clipboard"""
    selection = table_widget.selection()
    if not selection:
        return

    columns = table_widget["columns"]
    lines = ["\t".join(str(col) for col in columns)]

    for item in selection:
        values = table_widget.item(item)["values"]
        lines.append("\t".join(str(val) for val in values))

    text = "\n".join(lines)
    root.clipboard_clear()
    root.clipboard_append(text)
