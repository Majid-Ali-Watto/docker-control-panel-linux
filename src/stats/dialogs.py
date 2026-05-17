"""
Stats dialogs: docker disk usage view.
"""

import tkinter as tk
from tkinter import ttk

from src.docker.actions import check_docker_running
from src.config.config_manager import get_sudo_password
from src.utils.utils import async_run, parse_fixed_width_table
from src.ui.ui_components import create_table_widget
from src.docker.commands import DOCKER_DISK_USAGE_VERBOSE


def docker_disk_usage_view(output_container, loading_callback):
    """Show Docker disk usage in tabbed view"""
    if not check_docker_running(): return

    def callback(result):
        for widget in output_container.winfo_children():
            widget.pack_forget()

        disk_usage_frame = ttk.Frame(output_container)
        disk_usage_frame.pack(fill=tk.BOTH, expand=True)

        search_frame = ttk.Frame(disk_usage_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        search_label = ttk.Label(search_frame, text="🔍 Search:", font=("Arial", 10))
        search_label.pack(side=tk.LEFT, padx=(0, 5))

        disk_search_entry = ttk.Entry(search_frame, font=("Arial", 10))
        disk_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        disk_tables_data = []

        def perform_disk_search(*args):
            query = disk_search_entry.get().lower().strip()

            for table_widget, original_rows, columns in disk_tables_data:
                for item in table_widget.get_children():
                    table_widget.delete(item)

                for row in original_rows:
                    row_text = ' '.join(str(val).lower() for val in row)
                    if query == '' or query in row_text:
                        table_widget.insert("", tk.END, values=row)

        disk_search_entry.bind('<KeyRelease>', perform_disk_search)

        notebook = ttk.Notebook(disk_usage_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        lines = result.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]

            if line.startswith("Images space usage"):
                header = lines[i + 2]
                data = []
                i += 3
                while i < len(lines) and lines[i].strip():
                    data.append(lines[i])
                    i += 1

                cols, rows = parse_fixed_width_table(data, header)
                tab = ttk.Frame(notebook)
                notebook.add(tab, text="Images")
                table = create_table_widget(tab, cols)
                for r in rows:
                    table.insert("", tk.END, values=r)
                disk_tables_data.append((table, rows, cols))

            elif line.startswith("Containers space usage"):
                header = lines[i + 2]
                data = []
                i += 3
                while i < len(lines) and lines[i].strip():
                    data.append(lines[i])
                    i += 1

                cols, rows = parse_fixed_width_table(data, header)
                tab = ttk.Frame(notebook)
                notebook.add(tab, text="Containers")
                table = create_table_widget(tab, cols)
                for r in rows:
                    table.insert("", tk.END, values=r)
                disk_tables_data.append((table, rows, cols))

            elif line.startswith("Local Volumes space usage"):
                header = lines[i + 2]
                data = []
                i += 3
                while i < len(lines) and lines[i].strip():
                    data.append(lines[i])
                    i += 1

                cols, rows = parse_fixed_width_table(data, header)
                tab = ttk.Frame(notebook)
                notebook.add(tab, text="Volumes")
                table = create_table_widget(tab, cols)
                for r in rows:
                    table.insert("", tk.END, values=r)
                disk_tables_data.append((table, rows, cols))

            elif line.startswith("Build cache usage"):
                header = lines[i + 2]
                data = []
                i += 3
                while i < len(lines) and lines[i].strip():
                    data.append(lines[i])
                    i += 1

                cols, rows = parse_fixed_width_table(data, header)
                tab = ttk.Frame(notebook)
                notebook.add(tab, text="Build Cache")
                table = create_table_widget(tab, cols)
                for r in rows:
                    table.insert("", tk.END, values=r)
                disk_tables_data.append((table, rows, cols))

            i += 1

    async_run(DOCKER_DISK_USAGE_VERBOSE, callback, sudo=True, sudo_password=get_sudo_password(),
             loading_callback=loading_callback)
