"""
"How it works" card on the Docker home page: the path a button press takes (app → docker CLI →
engine → your containers), filled with what is really in use on this machine. Drawn on a canvas
that follows the theme and re-flows from one row to one column on narrow windows.
"""

import tkinter as tk
from tkinter import font as tkfont, ttk

from src.ui.rounded import mix_colors, readable, surface_color
from src.ui.ui_components import Tooltip
from src.utils.threads import startThreadForTask

_WIDE = 700                       # below this width the nodes stack vertically
_ARROWS = ("runs", "API", "owns")


def build_nodes(info):
    """[(title, [lines])] for the four stages, from an overview dict (system.overview.gather_overview)."""
    name = info.get("engine") or "docker"
    podman = name == "podman"
    access = ("through sudo with the saved password" if info.get("access") == "sudo"
              else "directly (no sudo needed)")
    server = info.get("server_version")
    if podman:
        engine_lines = ["no daemon: containers run", "straight from the CLI", "(experimental)"]
    elif server:
        engine_lines = [f"dockerd {server}", info.get("host") or "default socket",
                        f"managed by {info.get('init') or 'no init system'}"]
    else:
        engine_lines = ["not reachable", info.get("host") or "is Docker running?",
                        f"managed by {info.get('init') or 'no init system'}"]
    containers, running, images = info.get("containers"), info.get("running"), info.get("images")
    if containers is not None:
        resource_lines = [f"{running} of {containers} containers running", f"{images} images",
                          info.get("os") or ""]
    else:
        resource_lines = ["containers, images,", "volumes and networks", "appear here"]
    cli_version = info.get("client_version")
    return [
        ("This app", ["Docker Control Panel", "builds a command", "for every button"]),
        (f"{name} CLI", [info.get("cli_path") or f"{name} not found",
                         f"version {cli_version}" if cli_version else "version unknown", f"run {access}"]),
        ("Podman" if podman else "Docker Engine", engine_lines),
        ("Your " + ("Podman" if podman else "Docker"), resource_lines),
    ]


def _rounded(canvas, x1, y1, x2, y2, radius, **kw):
    points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius, x2, y2 - radius, x2, y2,
              x2 - radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
    return canvas.create_polygon(points, smooth=True, **kw)


class WorkflowDiagram(ttk.LabelFrame):
    def __init__(self, parent, fetch, text="How it works"):
        """fetch() -> overview dict; it runs on a worker thread."""
        super().__init__(parent, text=text, padding=(10, 8))
        self._fetch = fetch
        self._info, self._busy, self._again = None, False, False
        head = ttk.Frame(self)
        head.pack(fill=tk.X)
        self._caption = ttk.Label(head, text="Checking what is in use…", style="Muted.TLabel", font=("Arial", 8))
        self._caption.pack(side=tk.LEFT)
        reload_button = ttk.Button(head, text="↻ Refresh", style="secondary.TButton", width=10, command=self.refresh)
        reload_button.pack(side=tk.RIGHT)
        Tooltip(reload_button, "Check again which CLI, engine and socket are in use")
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, height=140, bg=surface_color())
        self.canvas.pack(fill=tk.X, pady=(6, 0))
        self._redraw_job = None
        self.canvas.bind("<Configure>", lambda _e: self._schedule_draw(), add="+")
        self.bind("<<ThemeChanged>>", lambda _e: self._schedule_draw(), add="+")
        self.bind("<Destroy>", lambda e: e.widget is self and self._cancel_draw(), add="+")

    # ── data ────────────────────────────────────────────────────────────────
    def refresh(self):
        """Look again at the system; the card keeps showing the last result meanwhile."""
        if self._busy:
            self._again = True
            return
        self._busy = True

        def task():
            try:
                info = self._fetch()
            except Exception:
                info = None
            self.after(0, lambda: self._done(info))
        startThreadForTask(task)

    def _done(self, info):
        if not self.winfo_exists():
            return
        self._busy = False
        if info is not None:
            self._info = info
        self._caption.configure(text="Live: what this machine is using right now"
                                if self._info else "Could not read the Docker setup.")
        self._schedule_draw()
        if self._again:
            self._again = False
            self.refresh()

    # ── drawing ─────────────────────────────────────────────────────────────
    def _schedule_draw(self):
        if self._redraw_job is None:
            self._redraw_job = self.after(30, self._draw)

    def _cancel_draw(self):
        if self._redraw_job is not None:
            self.after_cancel(self._redraw_job)
            self._redraw_job = None

    def _palette(self):
        surface = surface_color()
        text = ttk.Style().lookup("TLabel", "foreground") or "#dddddd"
        accents, danger = ["#4ea8f7", "#3fb950", "#d29922", "#a371f7"], "#f85149"
        try:      # the theme's own accent colours when ttkbootstrap provides them
            import ttkbootstrap as ttkbs
            colors = ttkbs.Style().colors
            themed = [colors.primary, colors.success, colors.warning, colors.info, colors.danger]
            if all(isinstance(c, str) and c for c in themed):
                accents, danger = themed[:4], themed[4]
        except Exception:
            pass
        card = mix_colors(surface, text, 0.07)
        return {"surface": surface, "card": card, "border": mix_colors(surface, text, 0.28),
                "text": readable(text, card), "muted": readable(mix_colors(text, surface, 0.4), card, 3),
                "accents": accents, "ok": accents[1], "danger": danger}

    @staticmethod
    def _fit(text, font, pixels):
        """`text` shortened with … so it is at most `pixels` wide."""
        if font.measure(text) <= pixels:
            return text
        while text and font.measure(text + "…") > pixels:
            text = text[:-1]
        return text + "…"

    def _draw(self):
        self._redraw_job = None
        if not self.winfo_exists():
            return
        canvas = self.canvas
        canvas.delete("all")
        pal = self._palette()
        canvas.configure(bg=pal["surface"])
        width = max(canvas.winfo_width(), 320)
        info = self._info or {"engine": "docker"}
        nodes = build_nodes(info)
        title_font = tkfont.Font(root=self, family="Arial", size=10, weight="bold")
        small_title_font = tkfont.Font(root=self, family="Arial", size=9, weight="bold")
        body_font = tkfont.Font(root=self, family="Arial", size=9)
        horizontal = width >= _WIDE
        pad, gap = 4, 46 if horizontal else 30
        node_h = 112 if horizontal else 104
        node_w = (width - 2 * pad - 3 * gap) / 4 if horizontal else width - 2 * pad
        up = bool(info.get("server_version")) or info.get("engine") == "podman"
        for index, (title, lines) in enumerate(nodes):
            x = pad + index * (node_w + gap) if horizontal else pad
            y = pad if horizontal else pad + index * (node_h + gap)
            accent = pal["accents"][index % len(pal["accents"])]
            _rounded(canvas, x, y, x + node_w, y + node_h, 10, fill=pal["card"], outline=pal["border"])
            canvas.create_rectangle(x + 10, y + 1, x + node_w - 10, y + 4, fill=accent, outline="")
            canvas.create_oval(x + 10, y + 14, x + 30, y + 34, fill=accent, outline="")
            canvas.create_text(x + 20, y + 24, text=str(index + 1), fill="#ffffff" if index == 0 else "#000000",
                               font=("Arial", 9, "bold"))
            room = node_w - 38 - (28 if index == 2 else 10)       # the engine node also has a status dot
            font = title_font if title_font.measure(title) <= room else small_title_font
            canvas.create_text(x + 38, y + 24, text=self._fit(title, font, room), anchor="w",
                               fill=pal["text"], font=font)
            if index == 2:     # engine reachable or not
                canvas.create_oval(x + node_w - 20, y + 19, x + node_w - 10, y + 29,
                                   fill=pal["ok"] if up else pal["danger"], outline="")
            for row, line in enumerate(lines):
                canvas.create_text(x + 14, y + 52 + row * 18, text=self._fit(line, body_font, node_w - 26),
                                   anchor="w", fill=pal["text"] if row == 0 else pal["muted"], font=body_font)
            if index < 3:
                label = _ARROWS[index]
                if horizontal:
                    ax1, ax2, ay = x + node_w + 4, x + node_w + gap - 4, y + node_h / 2
                    canvas.create_line(ax1, ay, ax2, ay, arrow=tk.LAST, width=2, fill=pal["muted"])
                    canvas.create_text((ax1 + ax2) / 2, ay - 10, text=label, fill=pal["muted"], font=("Arial", 8))
                else:
                    ax, ay1, ay2 = x + node_w / 2, y + node_h + 3, y + node_h + gap - 3
                    canvas.create_line(ax, ay1, ax, ay2, arrow=tk.LAST, width=2, fill=pal["muted"])
                    canvas.create_text(ax + 10, (ay1 + ay2) / 2, text=label, anchor="w", fill=pal["muted"],
                                       font=("Arial", 8))
        total = node_h + 2 * pad if horizontal else 4 * node_h + 3 * gap + 2 * pad
        canvas.configure(height=total)
