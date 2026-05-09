"""
Keyboard Navigation Module
Handles keyboard navigation and shortcuts for the application.
"""

import tkinter as tk
from tkinter import ttk


def enable_button_enter_key(button):
    """Enable Enter key to activate button when focused"""
    def on_enter(event):
        button.invoke()
        return "break"
    button.bind("<Return>", on_enter)
    button.bind("<KP_Enter>", on_enter)  # Numeric keypad Enter


def setup_keyboard_navigation(widget):
    """Setup keyboard navigation for a widget and its children"""
    # Enable tab traversal for all widgets
    if isinstance(widget, (ttk.Button, ttk.Entry, ttk.Combobox, ttk.Checkbutton)):
        widget.configure(takefocus=True)
        
        # Enable Enter key for buttons
        if isinstance(widget, ttk.Button):
            enable_button_enter_key(widget)
    
    # Recursively setup for children
    for child in widget.winfo_children():
        setup_keyboard_navigation(child)


def focus_next_widget(event):
    """Focus next widget (Tab key handler)"""
    event.widget.tk_focusNext().focus()
    return "break"


def focus_prev_widget(event):
    """Focus previous widget (Shift+Tab key handler)"""
    event.widget.tk_focusPrev().focus()
    return "break"


def create_navigation_handlers(btn_frame, active_sidebar_button_ref):
    """Create navigation handlers for moving between sidebar and main buttons"""
    def move_to_main_buttons(event):
        """Move focus from sidebar to main category buttons (Ctrl+Right)"""
        if btn_frame.winfo_children():
            for child in btn_frame.winfo_children():
                if isinstance(child, ttk.Button) and child.winfo_viewable():
                    child.focus()
                    return "break"
        return "break"

    def move_to_sidebar(event):
        """Move focus from main buttons to active sidebar button (Ctrl+Left)"""
        if active_sidebar_button_ref.get('button'):
            active_sidebar_button_ref['button'].focus()
        return "break"
    
    return move_to_main_buttons, move_to_sidebar


def bind_global_navigation(root):
    """Bind global keyboard navigation shortcuts"""
    # Bind global Tab and Shift+Tab for focus navigation
    root.bind_class("Button", "<Tab>", focus_next_widget)
    root.bind_class("Button", "<Shift-Tab>", focus_prev_widget)
    root.bind_class("Entry", "<Tab>", focus_next_widget)
    root.bind_class("Entry", "<Shift-Tab>", focus_prev_widget)
    root.bind_class("TCombobox", "<Tab>", focus_next_widget)
    root.bind_class("TCombobox", "<Shift-Tab>", focus_prev_widget)
    
    # Add standard text editing shortcuts for Entry widgets (Linux fix)
    def select_all(event):
        event.widget.select_range(0, tk.END)
        event.widget.icursor(tk.END)
        return "break"
    
    root.bind_class("Entry", "<Control-a>", select_all)
    root.bind_class("Entry", "<Control-A>", select_all)
