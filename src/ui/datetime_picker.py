"""
Date and time picker dialog (month calendar + hour/minute spinners).

ttkbootstrap's own DatePickerDialog has no time of day, so this small dialog is used for the
"Custom range" From/To fields of the table date filter.
"""

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

DATE_FORMAT = "%Y-%m-%d %H:%M"
_WEEKDAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")


class DateTimePicker(tk.Toplevel):
    """Modal picker. After it closes, ``result`` is a datetime (OK), "" (Clear) or None (Cancel)."""

    def __init__(self, parent, initial=None, default_time=(0, 0), title="Select date and time"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.result = None

        start = initial or datetime.now().replace(hour=default_time[0], minute=default_time[1],
                                                  second=0, microsecond=0)
        self._selected = start.date()
        self._year, self._month = start.year, start.month
        self._hour = tk.StringVar(master=self, value=f"{start.hour:02d}")
        self._minute = tk.StringVar(master=self, value=f"{start.minute:02d}")

        body = ttk.Frame(self, padding=14)
        body.pack()

        nav = ttk.Frame(body)
        nav.pack(fill=tk.X)
        for text, step, side in (("«", -12, tk.LEFT), ("‹", -1, tk.LEFT), ("»", 12, tk.RIGHT), ("›", 1, tk.RIGHT)):
            ttk.Button(nav, text=text, width=3, style="secondary.Outline.TButton",
                       command=lambda s=step: self._shift_month(s)).pack(side=side, padx=2)
        self._title_label = ttk.Label(nav, font=("Arial", 11, "bold"), anchor=tk.CENTER)
        self._title_label.pack(fill=tk.X, expand=True)

        self._grid_frame = ttk.Frame(body)
        self._grid_frame.pack(pady=10)

        time_row = ttk.Frame(body)
        time_row.pack()
        ttk.Label(time_row, text="🕒 Time", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 8))
        self._hour_spin = ttk.Spinbox(time_row, from_=0, to=23, width=3, wrap=True,
                                      textvariable=self._hour, format="%02.0f", justify=tk.CENTER)
        self._hour_spin.pack(side=tk.LEFT)
        ttk.Label(time_row, text=":", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=3)
        self._minute_spin = ttk.Spinbox(time_row, from_=0, to=59, width=3, wrap=True,
                                        textvariable=self._minute, format="%02.0f", justify=tk.CENTER)
        self._minute_spin.pack(side=tk.LEFT)

        actions = ttk.Frame(body)
        actions.pack(fill=tk.X, pady=(14, 0))
        ttk.Button(actions, text="Today", style="secondary.TButton", command=self._today).pack(side=tk.LEFT)
        ttk.Button(actions, text="Clear", style="secondary.Outline.TButton",
                   command=self._clear).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="OK", style="primary.TButton", width=7,
                   command=self._ok).pack(side=tk.RIGHT)
        ttk.Button(actions, text="Cancel", style="secondary.Outline.TButton", width=7,
                   command=self.destroy).pack(side=tk.RIGHT, padx=6)

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._ok())
        self._draw_month()

    # ---- calendar ----------------------------------------------------------

    def _draw_month(self):
        self._title_label.configure(text=f"{calendar.month_name[self._month]} {self._year}")
        for widget in self._grid_frame.winfo_children():
            widget.destroy()
        for col, name in enumerate(_WEEKDAYS):
            ttk.Label(self._grid_frame, text=name, font=("Arial", 9, "bold"),
                      anchor=tk.CENTER, width=4).grid(row=0, column=col, pady=(0, 4))
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(self._year, self._month)
        today = date.today()
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                in_month = day.month == self._month
                if day == self._selected:
                    style = "primary.TButton"
                elif day == today:
                    style = "info.Outline.TButton"
                else:
                    style = "secondary.Outline.TButton"
                button = ttk.Button(self._grid_frame, text=str(day.day), width=3, style=style,
                                    command=lambda d=day: self._select(d))
                if not in_month:
                    button.state(["disabled"])
                button.grid(row=row, column=col, padx=1, pady=1)

    def _shift_month(self, months):
        index = self._year * 12 + (self._month - 1) + months
        self._year, self._month = divmod(index, 12)
        self._month += 1
        self._draw_month()

    def _select(self, day):
        self._selected = day
        self._draw_month()

    def _today(self):
        now = datetime.now()
        self._selected = now.date()
        self._year, self._month = now.year, now.month
        self._hour.set(f"{now.hour:02d}")
        self._minute.set(f"{now.minute:02d}")
        self._draw_month()

    # ---- results -----------------------------------------------------------

    @staticmethod
    def _clamp(text, high):
        try:
            return max(0, min(high, int(float(text))))
        except ValueError:
            return 0

    def selected_datetime(self):
        return datetime(self._selected.year, self._selected.month, self._selected.day,
                        self._clamp(self._hour.get(), 23), self._clamp(self._minute.get(), 59))

    def _ok(self):
        self.result = self.selected_datetime()
        self.destroy()

    def _clear(self):
        self.result = ""
        self.destroy()


def pick_datetime(parent, initial=None, default_time=(0, 0), title="Select date and time"):
    """Show the picker modally; returns a datetime, "" when cleared, or None when cancelled."""
    dialog = DateTimePicker(parent, initial=initial, default_time=default_time, title=title)
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_reqwidth()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_reqheight()) // 3
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_set()
    dialog.wait_window()
    return dialog.result
