"""
UI Display Module
Handles display of tables, text output, and search functionality.
"""

import re
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk
from tkinter import font as tkfont
from src.ui.rounded import RoundedBadge, readable_color
from src.ui.cell_format import DATE_COLUMNS, DOCKER_DATE, format_cell, status_tone
from src.ui.table_cells import CellSelection
from src.ui.datetime_picker import DATE_FORMAT, pick_datetime
from src.ui.filter_popup import CUSTOM_RANGE, FilterPopup
from src.ui.ui_components import Tooltip
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
        self.search_entry = None
        self.live_stats_enabled = False
        self.live_stats_job = None
        
        # Action buttons (will be set by main)
        self.action_buttons = {}
        self.action_label = None

        # Re-runs the table view the user is looking at (set by the main window)
        self.view_refresh = None
        self.status_label = None
        self._columns, self._rows, self._shown = [], [], []
        self._sort_col, self._sort_reverse = None, False
        self._last_title = None
        self._chrome = []            # per-view widgets (search bar, title) discarded on rebuild
        self._empty_label = None
        self._badge = None           # "N items" count label next to the table title
        self._badge_noun = "item"
        self._date_col = None        # index of the CREATED column, when the table has one

        # Sort / date-filter state (persists while the same list is reloaded)
        self._sort_var = tk.StringVar(master=output_container, value=self._NO_SORT)
        self._preset_var = tk.StringVar(master=output_container, value="Any time")
        self._from_var = tk.StringVar(master=output_container)
        self._to_var = tk.StringVar(master=output_container)
        self._order_btn = None
        self._filter_btn = None
        self._filter_popup = None
        # The popup has no focus-out signal, so any click in the window outside the button dismisses it
        output_container.winfo_toplevel().bind("<Button-1>", self._dismiss_filter_popup, add="+")

        # "Back" bar shown above text output when a table view can be restored
        self._back_bar = ttk.Frame(output_container)
        ttk.Button(self._back_bar, text="← Back", style="secondary.TButton",
                   command=self.refresh_view).pack(side=tk.LEFT, padx=10, pady=(5, 0))

        # Row-action buttons wrap onto extra lines instead of running off-screen
        self._visible_action_buttons = []
        self.action_frame.bind("<Configure>", lambda e: self._layout_action_buttons())
        self.table_widget.bind("<<TreeviewSelect>>", lambda e: self.update_selection_state())
        self.table_widget.bind("<Double-1>", self._on_double_click)
        self.cells = CellSelection(table_widget, self.get_item_texts)
    
    def set_action_buttons(self, buttons_dict, action_label):
        """Set references to action buttons"""
        self.action_buttons = buttons_dict
        self.action_label = action_label
    
    def set_status(self, text, kind="info"):
        """Show a one-line result message under the table (kind: info | success | error)."""
        if not self.status_label or not self.status_label.winfo_exists():
            return
        style = {"success": "success.TLabel", "error": "danger.TLabel"}.get(kind, "Muted.TLabel")
        self.status_label.configure(text=text, style=style)

    def refresh_view(self):
        """Reload the current table view in place (no-op when no table view is active)."""
        if self.view_refresh:
            self.view_refresh()

    def cancel_running_operations(self):
        """Cancel any currently running operations"""
        cancel_current_operation()
        self.stop_live_stats()

    def stop_live_stats(self):
        """Stop any live stats refresh loop."""
        self.live_stats_enabled = False
        if self.live_stats_job:
            try:
                self.output_container.after_cancel(self.live_stats_job)
            except Exception:
                pass
            self.live_stats_job = None
    
    _STATUS_COLORS = {"bad": "#dc3545", "warn": "#d98200", "ok": "#2e9e5b"}

    def apply_status_colors(self):
        """Text colours for rows whose container needs attention (re-run on every theme change,
        since legibility depends on the surface behind the text)."""
        for tone, color in self._STATUS_COLORS.items():
            self.table_widget.tag_configure(f"status_{tone}", foreground=readable_color(color))

    def clear_table(self):
        """Clear all items from table"""
        for i in self.table_widget.get_children():
            self.table_widget.delete(i)
    
    # ---- table rendering -------------------------------------------------

    _FILTERABLE = ('container', 'container_stats', 'image', 'volume', 'network', 'compose',
                   'compose_service', 'disk_storage', 'disk_images', 'disk_containers',
                   'disk_volumes', 'disk_cache', 'context')
    _NOUNS = {'container': 'container', 'container_stats': 'container', 'image': 'image',
              'volume': 'volume', 'network': 'network', 'compose': 'project',
              'compose_service': 'service', 'disk_storage': 'row', 'disk_images': 'image',
              'disk_containers': 'container', 'disk_volumes': 'volume', 'disk_cache': 'record',
              'context': 'context'}
    _NO_SORT = "Original order"
    EMPTY_CELL = "—"
    _DATE_COLUMNS = DATE_COLUMNS
    _DATE_PRESETS = {
        "Any time": None,
        "Last hour": timedelta(hours=1),
        "Last 24 hours": timedelta(hours=24),
        "Last 7 days": timedelta(days=7),
        "Last 30 days": timedelta(days=30),
        CUSTOM_RANGE: None,
    }
    _DOCKER_DATE = DOCKER_DATE
    # Leading size such as '1.1GB', '25.9kB', '12.5MiB / 7.6GiB', '98kB (virtual 236MB)'.
    # Docker prints decimal units (kB/MB/GB) in ls/ps/df and binary ones (KiB/MiB/GiB) in stats.
    _SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*([kmgtp]?)(i?)b(?=$|[\s/(])", re.IGNORECASE)
    _NUMBER = re.compile(r"-?\d+(?:\.\d+)?%?")
    # Relative ages as printed by `docker system df -v`: '2 weeks ago', 'About an hour ago', '3 days'
    _AGE = re.compile(r"(?:about\s+)?(an?|\d+)\s+(second|minute|hour|day|week|month|year)s?(?:\s+ago)?$",
                      re.IGNORECASE)
    _AGE_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400,
                    "week": 604800, "month": 2592000, "year": 31536000}

    @classmethod
    def _parse_row_date(cls, text):
        """Parse docker's CreatedAt text (e.g. '2026-10-15 15:06:49 +0500 PKT'); None if absent."""
        m = cls._DOCKER_DATE.search(str(text))
        return datetime(*map(int, m.groups())) if m else None

    @staticmethod
    def _parse_user_date(text, end_of_day=False):
        """Parse 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'; None when empty or invalid."""
        text = text.strip()
        for fmt, date_only in (("%Y-%m-%d %H:%M", False), ("%Y-%m-%d", True)):
            try:
                value = datetime.strptime(text, fmt)
            except ValueError:
                continue
            if end_of_day:   # the "To" bound covers the whole day / whole minute that was given
                value += (timedelta(days=1) if date_only else timedelta(minutes=1)) - timedelta(seconds=1)
            return value
        return None

    def _date_bounds(self):
        """(earliest, latest) allowed creation time; None for an open end."""
        preset = self._preset_var.get()
        delta = self._DATE_PRESETS.get(preset)
        if delta:
            return datetime.now() - delta, None
        return (self._parse_user_date(self._from_var.get()),
                self._parse_user_date(self._to_var.get(), end_of_day=True))

    def _sort_key(self, row):
        """Comparable key for the sort column's cell, or None when it is empty.

        Sizes compare by bytes, numbers and percentages by value, dates by time and
        anything else case-insensitively with digit runs in numeric order (web2 < web10).
        Numeric keys rank before text so a mixed column never raises a TypeError.
        """
        text = str(row[self._sort_col]).strip() if self._sort_col < len(row) else ""
        if not text:
            return None
        if self._sort_col == self._date_col:
            created = self._parse_row_date(text)
            return (0, created.timestamp(), ()) if created else None
        age = self._AGE.match(text)
        if age:   # younger sorts higher, like a later timestamp
            count = 1 if age.group(1).lower() in ("a", "an") else int(age.group(1))
            return (0, -count * self._AGE_SECONDS[age.group(2).lower()], ())
        size = self._SIZE.match(text)
        if size:
            number, prefix, binary = size.groups()
            return (0, float(number) * (1024 if binary else 1000) ** ("_kmgtp".find(prefix.lower())), ())
        if self._NUMBER.fullmatch(text):
            return (0, float(text.rstrip("%")), ())
        parts = re.split(r"(\d+)", text.lower())   # str, digits, str, ... so positions always compare alike
        return (1, 0.0, tuple(int(p) if i % 2 else p for i, p in enumerate(parts)))

    def _visible_rows(self):
        """Rows after applying the search text, date filter and sort order."""
        query = self.search_entry.get().lower().strip() if self.search_entry else ""
        rows = [r for r in self._rows if not query or query in ' '.join(
            f"{v} {t}".lower() for v, t in zip(r, self._formatted(r)))]    # original and shown text

        if self._date_col is not None:
            lo, hi = self._date_bounds()
            if lo or hi:
                def in_range(row):
                    created = self._parse_row_date(row[self._date_col]) if self._date_col < len(row) else None
                    return created is not None and (not lo or created >= lo) and (not hi or created <= hi)
                rows = [r for r in rows if in_range(r)]

        if self._sort_col is not None:
            keyed, blanks = [], []
            for row in rows:
                key = self._sort_key(row)
                (blanks if key is None else keyed).append((key, row))
            keyed.sort(key=lambda pair: pair[0], reverse=self._sort_reverse)
            rows = [row for _, row in keyed + blanks]   # empty / unparsable cells stay last in either direction
        return rows

    def _formatted(self, row):
        """A row's cells as the user reads them (dates, sizes, ports tidied; blanks stay blank)."""
        return [format_cell(self._columns[i] if i < len(self._columns) else "", v)
                for i, v in enumerate(row)]

    def _row_key(self, iid):
        """Identity of a shown row (its first column), stable across reloads; None if unknown."""
        if iid is None or int(iid) >= len(self._shown) or not self._shown[int(iid)]:
            return None
        return str(self._shown[int(iid)][0])

    def _populate(self):
        """Fill the Treeview from the stored rows (filter + sort applied), keeping the selection
        and the active cell. Cells are shown tidied (see cell_format) and empty ones as EMPTY_CELL;
        the stored rows keep the original text for sorting, filtering and row actions."""
        selected_keys = {self._row_key(i) for i in self.table_widget.selection()} - {None}
        cell_key = self._row_key(self.cells.iid)
        self.clear_table()
        rows = self._shown = self._visible_rows()
        status_col = self._columns.index("STATUS") if "STATUS" in self._columns else None
        for idx, row in enumerate(rows, start=1):
            tags = ['evenrow' if idx % 2 == 0 else 'oddrow']
            tone = status_tone(row[status_col]) if status_col is not None and status_col < len(row) else None
            if tone:
                tags.append(f"status_{tone}")
            shown = [t if t.strip() else self.EMPTY_CELL for t in self._formatted(row)]
            self.table_widget.insert("", tk.END, iid=str(idx - 1), values=[idx] + shown, tags=tuple(tags))
        keep = [str(i) for i, row in enumerate(rows) if row and str(row[0]) in selected_keys]
        if keep:
            self.table_widget.selection_set(keep)
        self.cells.move_to_row(next((i for i in keep if self._row_key(i) == cell_key), None))

        if self._empty_label:
            if rows:
                self._empty_label.place_forget()
            else:
                msg = "No matches for the current filters." if self._rows else "Nothing to show here yet."
                self._empty_label.configure(text=msg)
                self._empty_label.place(relx=0.5, rely=0.45, anchor="center")
        if self._badge and self._badge.winfo_exists():
            total, shown = len(self._rows), len(rows)
            count = f"{shown} of {total}" if shown != total else f"{total}"
            self._badge.set_text(f"{count} {self._badge_noun}{'s' if total != 1 else ''}")
        self._update_headings()
        self.update_selection_state()

    def _update_headings(self):
        for i, col in enumerate(self._columns):
            arrow = ""
            if self._sort_col == i:
                arrow = "  ▼" if self._sort_reverse else "  ▲"
            self.table_widget.heading(col, text=col + arrow, command=lambda i=i: self.sort_by(i))
        # Keep the sort dropdown and order button in step with header clicks
        self._sort_var.set(self._columns[self._sort_col] if self._sort_col is not None else self._NO_SORT)
        if self._order_btn and self._order_btn.winfo_exists():
            self._order_btn.configure(text="↓ Desc" if self._sort_reverse else "↑ Asc")
            self._order_btn.state(['disabled'] if self._sort_col is None else ['!disabled'])
        if self._filter_btn and self._filter_btn.winfo_exists():
            active = self._filters_active()
            self._filter_btn.configure(text="☰ Filters ●" if active else "☰ Filters",
                                       style="primary.TButton" if active else "secondary.Outline.TButton")

    def sort_by(self, col_index):
        """Sort by a column; clicking the same column again reverses the order."""
        self._sort_reverse = (not self._sort_reverse) if self._sort_col == col_index else False
        self._sort_col = col_index
        self._populate()

    def _on_sort_selected(self, _event=None):
        choice = self._sort_var.get()
        if choice == self._NO_SORT or choice not in self._columns:
            self._sort_col, self._sort_reverse = None, False
        else:
            self._sort_col = self._columns.index(choice)
            self._sort_reverse = (self._sort_col == self._date_col)   # newest first for dates
        self._populate()

    def _toggle_sort_order(self):
        if self._sort_col is not None:
            self._sort_reverse = not self._sort_reverse
            self._populate()

    def _pick_date(self, var, end_of_day):
        """Open the calendar/time picker for a From/To field."""
        current = self._parse_user_date(var.get())
        chosen = pick_datetime(self.output_container.winfo_toplevel(), initial=current,
                               default_time=(23, 59) if end_of_day else (0, 0),
                               title="Select " + ("end" if end_of_day else "start") + " date and time")
        if chosen is None:
            return
        var.set(chosen.strftime(DATE_FORMAT) if chosen else "")

    def _apply_filters(self, preset, date_from, date_to):
        """Commit the filter popup's choice."""
        self._preset_var.set(preset)
        self._from_var.set(date_from)
        self._to_var.set(date_to)
        self._populate()

    def _clear_filters(self):
        """Reset search text and date filter (the sort choice is kept)."""
        if self.search_entry:
            self.search_entry.delete(0, tk.END)
        self._apply_filters("Any time", "", "")

    def _toggle_filter_popup(self):
        if self._close_filter_popup():
            return
        self._filter_popup = FilterPopup(
            self._filter_btn, list(self._DATE_PRESETS), self._preset_var.get(),
            self._from_var.get(), self._to_var.get(), self._pick_date,
            on_apply=self._apply_filters, on_clear=self._clear_filters)

    def _close_filter_popup(self):
        """Close the popup if it is open; True when there was one."""
        popup, self._filter_popup = self._filter_popup, None
        if popup and popup.winfo_exists():
            popup.close()
            return True
        return False

    def _dismiss_filter_popup(self, event):
        if self._filter_popup and event.widget is not self._filter_btn:
            self._close_filter_popup()

    _FONT = ("Arial", 10)
    _HEADER_PACK = {"fill": tk.X, "padx": 10, "pady": (6, 4)}
    _COMBO_WIDTH = 16            # every filter dropdown shares one width

    def _build_header(self, table_type, table_title, previous_query, tabs=None, active_tab=None):
        """Optional tab strip, title + count badge, then (for list views) one toolbar: search,
        sort and, for tables with a date column, a filter button that opens the filter popup."""
        header = ttk.Frame(self.output_container)
        header.pack(**self._HEADER_PACK)
        self._chrome.append(header)

        if tabs:
            strip = ttk.Frame(header)
            strip.pack(fill=tk.X, pady=(0, 6))
            for label, command in tabs.items():
                ttk.Button(strip, text=label, command=command, width=14,
                           style="primary.TButton" if label == active_tab else "secondary.Outline.TButton"
                           ).pack(side=tk.LEFT, padx=(0, 5))

        if table_title:
            title_row = ttk.Frame(header)
            title_row.pack(fill=tk.X)
            ttk.Label(title_row, text=table_title, font=("Arial", 12, "bold"),
                      foreground=readable_color("#0066cc")).pack(side=tk.LEFT)
            self._badge_noun = self._NOUNS.get(table_type, 'item')
            self._badge = RoundedBadge(title_row)
            self._badge.pack(side=tk.LEFT, padx=(10, 0))
            ttk.Label(title_row, text="Click a cell + Ctrl+C to copy · double-click: details · "
                                      "right-click: actions · Ctrl/Shift+click or Ctrl+A: multi-select",
                      font=("Arial", 9, "italic"), foreground=readable_color("#6c757d")
                      ).pack(side=tk.RIGHT)

        if table_type not in self._FILTERABLE:
            return

        bar = ttk.Frame(header)
        bar.pack(fill=tk.X, pady=(6, 0))
        self._toolbar = bar
        bar.columnconfigure(1, weight=1)

        def label(text, column):
            ttk.Label(bar, text=text, font=self._FONT).grid(row=0, column=column, padx=(12 if column else 0, 5))

        label("Search", 0)
        self.search_entry = ttk.Entry(bar, font=self._FONT, width=18)
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind('<KeyRelease>', self.perform_search)
        self.search_entry.bind('<Escape>', lambda e: (self.search_entry.delete(0, tk.END),
                                                      self.perform_search()))
        if previous_query:
            self.search_entry.insert(0, previous_query)

        label("Sort", 2)
        sort_combo = ttk.Combobox(bar, textvariable=self._sort_var, state="readonly", font=self._FONT,
                                  width=self._COMBO_WIDTH, values=[self._NO_SORT] + self._columns)
        sort_combo.grid(row=0, column=3)
        sort_combo.bind("<<ComboboxSelected>>", self._on_sort_selected)
        self._order_btn = ttk.Button(bar, text="↑ Asc", style="secondary.TButton", width=7,
                                     command=self._toggle_sort_order)
        self._order_btn.grid(row=0, column=4, padx=(5, 0))
        Tooltip(self._order_btn, "Switch between ascending and descending order")

        if self._date_col is not None:
            self._filter_btn = ttk.Button(bar, text="☰ Filters", style="secondary.Outline.TButton", width=11,
                                          command=self._toggle_filter_popup)
            self._filter_btn.grid(row=0, column=5, padx=(12, 0))
            Tooltip(self._filter_btn, "Filter the list by creation date")

    def _filters_active(self):
        query = self.search_entry.get().strip() if self.search_entry else ""
        return bool(query) or (self._date_col is not None and any(self._date_bounds()))

    def perform_search(self, *args):
        """Filter the table based on the search query"""
        if self.search_entry:
            self._populate()

    def _fit_columns(self):
        """Size each column to its widest cell/heading (measured, bounded) so nothing is clipped
        and nothing is wastefully wide; the last column takes any leftover space."""
        body = tkfont.Font(font=("JetBrains Mono", 9))
        head = tkfont.Font(font=("Arial", 9, "bold"))
        texts = [self._formatted(row) for row in self._rows[:300]]
        for i, col in enumerate(self._columns):
            widest = head.measure(col) + 36            # room for the sort arrow
            for row in texts:
                if i < len(row):
                    widest = max(widest, body.measure(row[i]) + 24)
            self.table_widget.column(col, anchor=tk.W, width=min(max(widest, 70), 460),
                                     minwidth=70, stretch=(i == len(self._columns) - 1))

    # ---- row-action buttons ----------------------------------------------

    _ACTION_LAYOUT = {
        'container': ['start', 'stop', 'restart', 'pause', 'unpause', 'rename',
                      'delete', 'terminal', 'logs', 'details', 'top', 'diff', 'inspect_container',
                      'commit', 'export', 'browse_files'],
        'container_stats': ['start', 'stop', 'restart', 'pause', 'unpause',
                            'delete', 'terminal', 'logs', 'details', 'top', 'inspect_container'],
        'image': ['delete_image', 'push_image', 'run', 'stop_using', 'tag_image',
                  'save_image', 'scan_image', 'inspect_image', 'history_image'],
        'volume': ['delete_volume', 'inspect_volume'],
        'network': ['delete_network', 'inspect_network', 'connect_network', 'disconnect_network'],
        'disk_images': ['delete_image', 'scan_image', 'inspect_image', 'history_image'],
        'disk_containers': ['start', 'stop', 'restart', 'pause', 'unpause', 'delete', 'details',
                            'inspect_container'],
        'disk_volumes': ['delete_volume', 'inspect_volume'],
        'compose': ['compose_up', 'compose_up_build', 'compose_build', 'compose_pull',
                    'compose_restart', 'compose_stop', 'compose_down', 'compose_down_volumes',
                    'compose_logs', 'compose_services', 'compose_inspect'],
        'context': ['use_context', 'inspect_context'],
    }
    # Actions that operate on exactly one row (they prompt, open a window, or show one item)
    _SINGLE_ROW_ACTIONS = {
        'rename', 'terminal', 'logs', 'inspect_container', 'commit', 'browse_files',
        'details', 'top', 'diff', 'export', 'scan_image', 'use_context', 'inspect_context',
        'push_image', 'tag_image', 'save_image', 'inspect_image', 'history_image',
        'inspect_volume', 'inspect_network', 'connect_network', 'disconnect_network',
        'compose_logs', 'compose_services', 'compose_inspect',
    }

    def update_action_buttons(self):
        """Show/hide action buttons based on current table type"""
        for widget in self.action_frame.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.pack_forget()
                widget.grid_forget()
        self._visible_action_buttons = []

        names = self._ACTION_LAYOUT.get(self.current_table_type, [])
        for name in names:
            btn = self.action_buttons.get(name)
            if btn is not None and btn.winfo_exists():
                self._visible_action_buttons.append((name, btn))

        has_actions = bool(self._visible_action_buttons)
        if self.action_label and self.action_label.winfo_exists():
            if has_actions:
                self.action_label.grid(row=0, column=0, sticky="w", padx=(5, 10))
            else:
                self.action_label.grid_forget()

        self._layout_action_buttons()
        self.update_selection_state()

        # Stats control buttons (interval / Live Stats / Refresh) sit on the right of the same bar
        if self.current_table_type == 'container_stats':
            columns = {"⏱": 97, "Live Stats": 98, "Refresh": 99}
            for widget in self.action_frame.winfo_children():
                if isinstance(widget, ttk.Button):
                    key = next((k for k in columns if k in str(widget.cget("text"))), None)
                    if key:
                        widget.grid(row=0, column=columns[key], sticky="e", padx=5)
            self.action_frame.columnconfigure(96, weight=1)

    def _layout_action_buttons(self):
        """Grid the visible action buttons, wrapping onto new lines to fit the window width."""
        buttons = self._visible_action_buttons
        if not buttons:
            return
        available = self.action_frame.winfo_width()
        label_w = self.action_label.winfo_reqwidth() + 15 if self.action_label else 0
        cell_w = max(btn.winfo_reqwidth() for _, btn in buttons) + 6
        per_row = max(1, (available - label_w) // cell_w) if available > 1 else len(buttons)
        for i, (_, btn) in enumerate(buttons):
            btn.grid(row=i // per_row, column=1 + i % per_row, padx=2, pady=2, sticky="w")

    # Row action opened by double-clicking a row (the same button the toolbar shows)
    _DOUBLE_CLICK_ACTION = {
        'container': 'inspect_container', 'container_stats': 'inspect_container',
        'disk_containers': 'inspect_container', 'image': 'inspect_image',
        'disk_images': 'inspect_image', 'volume': 'inspect_volume',
        'disk_volumes': 'inspect_volume', 'network': 'inspect_network',
        'compose': 'compose_services', 'context': 'inspect_context',
    }

    def _on_double_click(self, event):
        if self.table_widget.identify_region(event.x, event.y) != "cell":
            return
        button = self.action_buttons.get(self._DOUBLE_CLICK_ACTION.get(self.current_table_type))
        if button is not None and button.winfo_exists() and not button.instate(['disabled']):
            button.invoke()

    def row_actions(self):
        """(label, command, enabled) for each action button shown for the current list."""
        return [(btn.cget("text"), btn.invoke, not btn.instate(['disabled']))
                for _, btn in self._visible_action_buttons if btn.winfo_exists()]

    def update_selection_state(self):
        """Enable only the actions that make sense for the current selection."""
        count = len(self.table_widget.selection())
        for name, btn in self._visible_action_buttons:
            if not btn.winfo_exists():
                continue
            enabled = count >= 1 and not (count > 1 and name in self._SINGLE_ROW_ACTIONS)
            btn.state(['!disabled'] if enabled else ['disabled'])
        if self.action_label and self.action_label.winfo_exists():
            if count == 0:
                self.action_label.configure(text="Select a row to enable actions:")
            else:
                self.action_label.configure(text=f"{count} selected:")

    def _discard_view_chrome(self):
        for widget in self._chrome:
            widget.destroy()
        self._chrome = []
        self.search_entry = None
        self._badge = None
        self._close_filter_popup()
        self._order_btn = None
        self._filter_btn = None

    def show_table(self, columns, rows, table_type=None, table_title=None, append=False,
                   tabs=None, active_tab=None):
        """Show tabular data in Treeview.

        `tabs` ({label: callback}) adds a tab strip above the title, with `active_tab` highlighted.
        """
        # Cancel any running operations when starting a new view
        if not append:
            if table_type == 'container_stats' and self.live_stats_enabled:
                cancel_current_operation()
            else:
                self.cancel_running_operations()

        self.current_table_type = table_type

        # Keep the user's search text and sort order when the same view is reloaded in place
        same_view = (table_title == self._last_title and list(columns) == self._columns)
        previous_query = self.search_entry.get() if (same_view and self.search_entry) else ""
        if not same_view:
            self._sort_col, self._sort_reverse = None, False
            self._shown = []
            self._preset_var.set("Any time")
            self._from_var.set("")
            self._to_var.set("")
        self._columns = list(columns)
        self._date_col = next((i for i, c in enumerate(self._columns) if c in self._DATE_COLUMNS), None)
        self._last_title = table_title

        if not append:
            for widget in self.output_container.winfo_children():
                widget.pack_forget()
            if same_view and self._chrome and not tabs:
                # Same list reloaded (e.g. live stats): keep the header so a half-typed search
                # keeps its focus and an open sort dropdown is not torn down
                self._close_filter_popup()
                for widget in self._chrome:
                    widget.pack(**self._HEADER_PACK)
            else:
                self._discard_view_chrome()
                self._build_header(table_type, table_title, previous_query, tabs, active_tab)

        self.table_frame.pack(fill=tk.BOTH, expand=True)

        self._rows = [list(r) for r in rows]
        if self._empty_label is None:
            self._empty_label = ttk.Label(self.table_widget, font=("Arial", 11))

        self.table_widget["columns"] = ["No."] + self._columns
        self.table_widget["show"] = "headings"
        self.table_widget.heading("No.", text="No.")
        self.table_widget.column("No.", anchor=tk.CENTER, width=50, stretch=False)
        self._fit_columns()

        self._populate()
        self.update_action_buttons()

    def show_text_output(self, text):
        """Show text output in Text widget"""
        # Cancel any running operations when starting a new view
        self.cancel_running_operations()

        self.current_table_type = None

        # Clear output container and recreate frames
        for widget in self.output_container.winfo_children():
            widget.pack_forget()

        # Offer a way back to the list the user came from
        if self.view_refresh:
            self._back_bar.pack(fill=tk.X)

        self.text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)

        # Hide action buttons
        self.update_action_buttons()

    def select_all_rows(self):
        """Select every row currently shown (after search and filters)."""
        rows = self.table_widget.get_children()
        self.table_widget.selection_set(rows)
        self.update_selection_state()
        self.set_status(f"Selected {len(rows)} row{'s' if len(rows) != 1 else ''}")

    def get_selected_items(self):
        """Get selected items from table"""
        return self.table_widget.selection()
    
    def get_item_values(self, item):
        """A row as stored: serial number, then the original cell text (empty cells stay empty)."""
        if int(item) < len(self._shown):
            return [int(item) + 1] + list(self._shown[int(item)])
        return self.table_widget.item(item)["values"]

    def get_item_texts(self, item):
        """A row as shown (serial number first), except that empty cells are '' not EMPTY_CELL."""
        if int(item) < len(self._shown):
            return [int(item) + 1] + self._formatted(self._shown[int(item)])
        return self.table_widget.item(item)["values"]

    def selected_rows_text(self):
        """Selected rows as shown, tab-separated under a header line, ready for the clipboard."""
        lines = ["\t".join(["No."] + self._columns)]
        lines += ["\t".join(str(v) for v in self.get_item_texts(i)) for i in self.get_selected_items()]
        return "\n".join(lines)
