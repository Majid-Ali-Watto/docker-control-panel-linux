"""
UI Display Module
Handles display of tables, text output, and search functionality.
"""

import tkinter as tk
from tkinter import ttk
from src.utils.utils import cancel_current_operation


class DisplayManager:
    """Manages output display (tables and text)"""
    
    def __init__(self, output_container, table_frame, text_frame, table_widget, text_widget, action_frame):
        self.output_container = output_container
        self.table_frame = table_frame
        self.text_frame = text_frame
        self.table_widget = table_widget
        self.text_widget = text_widget
        self.action_frame = action_frame
        
        # State tracking
        self.current_table_type = None
        self.all_tables_data = []
        self.search_entry = None
        
        # Action buttons (will be set by main)
        self.action_buttons = {}
        self.action_label = None
    
    def set_action_buttons(self, buttons_dict, action_label):
        """Set references to action buttons"""
        self.action_buttons = buttons_dict
        self.action_label = action_label
    
    def cancel_running_operations(self):
        """Cancel any currently running operations"""
        cancel_current_operation()
    
    def clear_table(self):
        """Clear all items from table"""
        for i in self.table_widget.get_children():
            self.table_widget.delete(i)
    
    def perform_search(self, *args):
        """Filter all tables based on search query"""
        if not self.search_entry:
            return
        
        query = self.search_entry.get().lower().strip()
        
        # Filter each table
        for table_widget, original_rows, columns in self.all_tables_data:
            # Clear table
            for item in table_widget.get_children():
                table_widget.delete(item)
            
            # Re-populate with filtered data
            idx = 1
            for row in original_rows:
                # Search in all columns
                row_text = ' '.join(str(val).lower() for val in row)
                if query == '' or query in row_text:
                    row_with_sno = [idx] + list(row)
                    tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                    table_widget.insert("", tk.END, values=row_with_sno, tags=(tag,))
                    idx += 1
    
    def update_action_buttons(self):
        """Show/hide action buttons based on current table type"""
        # Hide all buttons first
        for widget in self.action_frame.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.pack_forget()
        
        # Show label always (check if it still exists)
        if self.action_label and self.action_label.winfo_exists():
            self.action_label.pack(side=tk.LEFT, padx=5)
        
        # Show buttons based on table type
        if self.current_table_type == 'container':
            for btn_name in ['start', 'stop', 'delete', 'terminal', 'logs']:
                if btn_name in self.action_buttons and self.action_buttons[btn_name].winfo_exists():
                    self.action_buttons[btn_name].pack(side=tk.LEFT, padx=2)
        elif self.current_table_type == 'container_stats':
            # For container stats, show regular container action buttons
            for btn_name in ['start', 'stop', 'delete', 'terminal', 'logs']:
                if btn_name in self.action_buttons and self.action_buttons[btn_name].winfo_exists():
                    self.action_buttons[btn_name].pack(side=tk.LEFT, padx=2)
            # And also show refresh button
            for widget in self.action_frame.winfo_children():
                if isinstance(widget, ttk.Button) and "Refresh" in str(widget.cget("text")):
                    widget.pack(side=tk.RIGHT, padx=5)
                    break
        elif self.current_table_type == 'image':
            for btn_name in ['delete_image', 'run', 'stop_using']:
                if btn_name in self.action_buttons and self.action_buttons[btn_name].winfo_exists():
                    self.action_buttons[btn_name].pack(side=tk.LEFT, padx=2)
        elif self.current_table_type == 'volume':
            if 'delete_volume' in self.action_buttons and self.action_buttons['delete_volume'].winfo_exists():
                self.action_buttons['delete_volume'].pack(side=tk.LEFT, padx=2)
    
    def show_table(self, columns, rows, table_type=None, table_title=None, append=False):
        """Show tabular data in Treeview"""
        # Cancel any running operations when starting a new view
        if not append:
            self.cancel_running_operations()
        
        self.current_table_type = table_type
        
        # Clear output container only if not appending
        if not append:
            for widget in self.output_container.winfo_children():
                widget.pack_forget()
            self.all_tables_data = []
            
            # Add search bar for Docker categories
            if table_type in ['container', 'image', 'volume']:
                search_frame = ttk.Frame(self.output_container)
                search_frame.pack(fill=tk.X, padx=10, pady=(5, 5))
                
                search_label = ttk.Label(search_frame, text="🔍 Search:", font=("Arial", 10))
                search_label.pack(side=tk.LEFT, padx=(0, 5))
                
                self.search_entry = ttk.Entry(search_frame, font=("Arial", 10))
                self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.search_entry.bind('<KeyRelease>', self.perform_search)
            
            # Add table title + count badge on the same row
            if table_title:
                title_frame = ttk.Frame(self.output_container)
                title_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

                ttk.Label(title_frame, text=table_title,
                          font=("Arial", 12, "bold"),
                          foreground="#0066cc").pack(side=tk.LEFT, anchor=tk.W)

                _noun = {'container': 'container', 'container_stats': 'container',
                         'image': 'image', 'volume': 'volume'}.get(table_type, 'item')
                _count = len(rows)
                _badge_text = f"  {_count} {_noun}{'s' if _count != 1 else ''}  "
                tk.Label(title_frame, text=_badge_text,
                         font=("Arial", 9, "bold"),
                         bg="#2563eb", fg="#ffffff",
                         relief="flat", padx=4, pady=2).pack(side=tk.LEFT, padx=(10, 0), anchor=tk.W)
        
        self.table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add serial number column
        columns_with_sno = ["No."] + columns
        self.table_widget["columns"] = columns_with_sno
        self.table_widget["show"] = "headings"
        
        # Configure No. column
        self.table_widget.heading("No.", text="No.")
        self.table_widget.column("No.", anchor=tk.CENTER, width=50)
        
        for col in columns:
            self.table_widget.heading(col, text=col)
            self.table_widget.column(col, anchor=tk.W, width=150)
        
        self.clear_table()
        for idx, row in enumerate(rows, start=1):
            row_with_sno = [idx] + list(row)
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            self.table_widget.insert("", tk.END, values=row_with_sno, tags=(tag,))
        
        # Store table data for search functionality
        self.all_tables_data.append((self.table_widget, rows, columns))
        
        # Update button visibility
        self.update_action_buttons()
    
    def show_text_output(self, text):
        """Show text output in Text widget"""
        # Cancel any running operations when starting a new view
        self.cancel_running_operations()
        
        self.current_table_type = None
        
        # Clear output container and recreate frames
        for widget in self.output_container.winfo_children():
            widget.pack_forget()
        
        self.text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)
        
        # Hide action buttons
        self.update_action_buttons()
    
    def get_selected_items(self):
        """Get selected items from table"""
        return self.table_widget.selection()
    
    def get_item_values(self, item):
        """Get values for a table item"""
        return self.table_widget.item(item)["values"]
