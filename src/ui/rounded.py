"""
Rounded corners for the UI.

Tk has no border-radius, so two techniques are used:
  * ttk widgets (buttons, entries, comboboxes, label frames): the rectangular border
    element of each style is swapped for an anti-aliased, nine-slice image drawn with
    the colours the ttkbootstrap theme already defines for every state.
  * plain tk surfaces (banner, count badge, loading card): ``RoundedPanel`` draws the
    rounded background on a Canvas and hosts the content in ``.body``.
"""

import base64
import io
import itertools
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageColor, ImageDraw

RADIUS = 8
_TILE = 128                     # side of the nine-slice source images
_SCALE = 4                      # supersampling factor for smooth edges
_COLORS = ("primary", "secondary", "success", "info", "warning", "danger", "light", "dark")

_images = {}                    # keeps PhotoImages alive and caches identical ones
_element_ids = itertools.count()
_panels = []
BUTTON_PALETTE = {}             # style name -> {state: (fill, text)} as actually drawn (for audits)
_tk_colors = []                 # (widget, {"bg"/"fg": colour}) for widgets built by make()


def _luminance(color):
    r, g, b = [v / 255 for v in ImageColor.getrgb(color)[:3]]
    lin = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    """WCAG contrast ratio between two colours (1 = identical, 21 = black on white)."""
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(round(v) for v in rgb)


def _blend(a, b, t):
    ra, rb = ImageColor.getrgb(a)[:3], ImageColor.getrgb(b)[:3]
    return _hex([x + (y - x) * t for x, y in zip(ra, rb)])


def readable(fg, bg, need=4.5):
    """`fg` itself when it is legible on `bg`; otherwise the same hue pushed towards black or
    white (whichever contrasts more) until it reaches `need`."""
    if not fg or not bg or contrast(fg, bg) >= need:
        return fg
    target = "#000000" if contrast("#000000", bg) >= contrast("#ffffff", bg) else "#ffffff"
    for step in range(1, 21):
        candidate = _blend(fg, target, step / 20)
        if contrast(candidate, bg) >= need:
            return candidate
    return target


def on_fill(fill, preferred, need=4.5):
    """Text colour for a filled surface: `preferred` if legible, else black or white."""
    if not preferred or contrast(preferred, fill) >= need:
        return preferred
    return "#000000" if contrast("#000000", fill) >= contrast("#ffffff", fill) else "#ffffff"


def surface_color():
    """Colour of ordinary (ttk) frames in the current theme."""
    return str(ttk.Style().lookup("TFrame", "background") or "#ffffff")


def readable_color(color, need=4.5):
    """Any Tk colour (name or #hex) adjusted to be legible on the current surface."""
    root = tk._default_root
    if root is not None and not str(color).startswith("#"):
        color = _hex([v / 257 for v in root.winfo_rgb(color)])
    return readable(color, surface_color(), need)


def _rgba(color):
    if not color:
        return (0, 0, 0, 0)
    try:
        return ImageColor.getcolor(color, "RGBA")
    except ValueError:
        return (0, 0, 0, 0)


def _rounded_image(master, width, height, radius, fill, outline=None, outline_width=1):
    """Anti-aliased rounded rectangle with transparent corners (fill/outline are colour strings)."""
    key = (str(master), width, height, radius, fill, outline, outline_width)
    if key in _images and _images[key].tk is master.tk:    # not one left by a destroyed Tk
        return _images[key]
    s = _SCALE
    img = Image.new("RGBA", (width * s, height * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    box = (0, 0, width * s - 1, height * s - 1)
    if outline:
        draw.rounded_rectangle(box, radius * s, fill=_rgba(outline))
        inset = outline_width * s
        draw.rounded_rectangle((inset, inset, width * s - 1 - inset, height * s - 1 - inset),
                               max(radius - outline_width, 0) * s, fill=_rgba(fill))
    else:
        draw.rounded_rectangle(box, radius * s, fill=_rgba(fill))
    png = io.BytesIO()
    img.resize((width, height), Image.LANCZOS).save(png, format="PNG")
    # Tk reads PNG (with alpha) natively, so Pillow's ImageTk module is not needed
    photo = tk.PhotoImage(master=master, data=base64.b64encode(png.getvalue()))
    _images[key] = photo
    return photo


def _swap_element(layout, old, new):
    """Copy of a ttk layout with element `old` renamed to `new` (its fixed border dropped).

    A style that inherits its layout may already carry another style's rounded element
    (named ``Rounded<N>.<old>``), so those are replaced too.
    """
    result = []
    for name, opts in layout:
        opts = dict(opts)
        if name == old or (name.startswith("Rounded") and name.endswith("." + old)):
            name = new
            opts.pop("border", None)
        if "children" in opts:
            opts["children"] = _swap_element(opts["children"], old, new)
        result.append((name, opts))
    return result


def _install(style, root, style_name, old_element, states, radius=RADIUS, padding=1):
    """Create an image element from `states` and make `style_name` use it.

    states: list of (state-tuple, fill, outline); the first entry is the normal look.
    """
    # Tk tiles the nine-slice centre; a large centre slice means few tiles to draw (a 3px
    # centre made wide widgets take seconds to repaint). width/height keep the minimum
    # widget size small regardless of the image size.
    size = _TILE
    images = [(st, _rounded_image(root, size, size, radius, fill, outline)) for st, fill, outline in states]
    name = f"Rounded{next(_element_ids)}.{old_element}"
    normal = images[0][1]
    style.element_create(name, "image", normal,
                         *[(*st, img) for st, img in images[1:] if st],
                         border=radius, padding=padding, sticky="nsew",
                         width=radius * 2 + 3, height=radius * 2 + 3)
    layout = style.layout(style_name)
    style.layout(style_name, _swap_element(layout, old_element, name))


def _lookup(style, name, option, state=None):
    value = style.lookup(name, option, state)
    return str(value) if value not in (None, "") else None


def _paint_behind(style, name, surface):
    """ttk paints the widget window with the style's `background`; it must equal the parent's
    colour in every state or the transparent corners would show a coloured square."""
    style.configure(name, background=surface)
    style.map(name, background=[])


def _round_buttons(style, root, surface):
    names = ["TButton"] + [f"{c}.TButton" for c in _COLORS] + [f"{c}.Outline.TButton" for c in _COLORS]
    # ttkbootstrap builds a style the first time a widget uses it; force them all to exist
    probes = [ttk.Button(root, style=n) for n in names]
    for probe in probes:
        probe.destroy()
    for name in names:
        def look(option, state):
            return _lookup(style, name, option, state)
        base_fill = look("background", None)
        base_edge = look("bordercolor", None) or base_fill
        outline = base_edge != base_fill          # outline buttons: coloured ring, plain fill
        fills, texts, edges = {}, {}, {}
        for st in ((), ("disabled",), ("pressed",), ("hover",), ("active",)):
            state = list(st) or None
            fill = look("background", state)
            edge = look("bordercolor", state) or fill
            text = look("foreground", state)
            need = 3 if st == ("disabled",) else 4.5
            if outline and not st:
                # accent-coloured text/ring on the theme surface: darken or lighten the accent
                accent = readable(edge, surface)
                fills[st], edges[st], texts[st] = fill, accent, accent
            else:
                fills[st] = fill
                edges[st] = edge if (outline or st == ("disabled",)) and edge != fill else None
                texts[st] = on_fill(fill, text, need) if not (outline and st == ("disabled",)) \
                    else readable(text, fill, need)
        states = [(st, fills[st], edges[st]) for st in fills]
        BUTTON_PALETTE[name] = {st: (fills[st], texts[st]) for st in fills}
        _install(style, root, name, "Button.border", states)
        _paint_behind(style, name, surface)
        style.configure(name, foreground=texts[()])
        style.map(name, foreground=[("disabled", texts[("disabled",)]),
                                    ("pressed", "!disabled", texts[("pressed",)]),
                                    ("hover", "!disabled", texts[("hover",)])])


def _round_fields(style, root, surface):
    for name, element, widget in (("TEntry", "Entry.field", ttk.Entry),
                                  ("TCombobox", "combo.Spinbox.field", ttk.Combobox)):
        widget(root).destroy()
        states = []
        for st in ((), ("disabled",), ("readonly",), ("invalid",), ("focus",), ("hover",)):
            fill = _lookup(style, name, "fieldbackground", list(st) or None)
            edge = _lookup(style, name, "bordercolor", list(st) or None)
            states.append((st, fill, edge))
        _install(style, root, name, element, states, padding=2)
        base_fill = _lookup(style, name, "fieldbackground")
        dim = _lookup(style, name, "foreground", ["disabled"])
        if dim and base_fill:
            style.map(name, foreground=[("disabled", readable(dim, base_fill, 3))])
        # the dropdown arrow is bottom-aligned by default; centre it vertically
        style.layout(name, _set_sticky(style.layout(name), "Combobox.downarrow", ""))
        _paint_behind(style, name, surface)


def _set_sticky(layout, element, sticky):
    result = []
    for name, opts in layout:
        opts = dict(opts)
        if name == element:
            opts["sticky"] = sticky
        if "children" in opts:
            opts["children"] = _set_sticky(opts["children"], element, sticky)
        result.append((name, opts))
    return result


def _round_frames(style, root):
    ttk.Labelframe(root).destroy()
    edge = _lookup(style, "TLabelframe", "bordercolor")
    _install(style, root, "TLabelframe", "Labelframe.border", [((), None, edge)], padding=0)


def _muted_label(style, surface):
    """"Muted.TLabel": the theme's text colour faded towards the surface, kept at 4.5:1 or more
    (ttkbootstrap's own ``secondary.TLabel`` is 1.6:1 on Darkly and Superhero)."""
    text = _lookup(style, "TLabel", "foreground")
    if text:
        style.configure("Muted.TLabel", foreground=readable(_blend(text, surface, 0.35), surface))


def apply_rounded_styles(style, root):
    """Round the ttk widgets of the current theme. Call again after every theme change."""
    surface = _lookup(style, "TFrame", "background") or "#222222"
    _muted_label(style, surface)
    _round_buttons(style, root, surface)
    _round_fields(style, root, surface)
    _round_frames(style, root)
    refresh_panels()


def _surface_of(widget):
    """Background colour a widget's parent shows (tk or ttk)."""
    try:
        return widget.cget("bg")
    except tk.TclError:
        return ttk.Style().lookup(widget.winfo_class(), "background") or "#ffffff"


class RoundedPanel(tk.Canvas):
    """A rounded, filled surface. Put content in ``panel.body`` (a tk.Frame)."""

    def __init__(self, parent, fill, radius=10, outline=None, padding=0, fit_width=False):
        super().__init__(parent, highlightthickness=0, bd=0)
        self.configure(bg=_surface_of(parent))
        self.fill, self.outline, self.radius = fill, outline, radius
        # inset the body so its square corners stay inside the rounded outline
        self._pad, self._fit_width = max(padding, -(-radius * 3 // 10) + 1), fit_width
        self._photo = None
        self.body = tk.Frame(self)
        self.body.configure(bg=fill)
        self._window = self.create_window(padding, padding, window=self.body, anchor="nw")
        self._centered = False
        self.bind("<Configure>", self._on_resize)
        self.body.bind("<Configure>", self._on_body_resize)
        _panels.append(self)

    def _on_body_resize(self, _event=None):
        height = self.body.winfo_reqheight() + 2 * self._pad
        self.configure(height=height)
        if self._fit_width:
            self.configure(width=self.body.winfo_reqwidth() + 2 * self._pad)

    def _on_resize(self, event):
        if self._fit_width:          # shrink-to-content panels: centre the body in the pill
            self.coords(self._window, event.width / 2, event.height / 2)
            self.itemconfigure(self._window, anchor="center")
        else:
            self.itemconfigure(self._window, width=max(event.width - 2 * self._pad, 1))
        self._redraw(event.width, event.height)

    def _redraw(self, width, height):
        if width < 2 or height < 2:
            return
        self.delete("surface")
        self._photo = _rounded_image(self, width, height, self.radius, self.fill, self.outline)
        self.create_image(0, 0, image=self._photo, anchor="nw", tags="surface")
        self.tag_lower("surface")

    def destroy(self):
        if self in _panels:          # short-lived panels (popup menus) must not pile up here
            _panels.remove(self)
        super().destroy()

    def refresh(self):
        """Re-read the parent's colour (after a theme change) and redraw."""
        self.configure(bg=_surface_of(self.master))
        self.body.configure(bg=self.fill)
        self._redraw(self.winfo_width(), self.winfo_height())


class RoundedBadge(RoundedPanel):
    """Small pill with text, e.g. the row-count badge."""

    def __init__(self, parent, text="", fill="#2563eb", fg="#ffffff", font=("Arial", 9, "bold"), radius=9):
        super().__init__(parent, fill, radius=radius, fit_width=True)
        self.label = tk.Label(self.body, text=text, font=font, padx=6, pady=1)
        self.label.configure(bg=fill, fg=fg)
        _tk_colors.append((self.label, {"bg": fill, "fg": fg}))
        self.label.pack()

    def set_text(self, text):
        self.label.configure(text=text)


def make(widget_class, parent, **options):
    """Create a plain tk widget and apply colours/fonts afterwards.

    ttkbootstrap restyles tk widgets at construction time and would discard bg/fg passed
    to the constructor; options given through configure() are kept. ttkbootstrap also resets
    tk widget colours when the theme changes, so the colours are remembered and restored by
    refresh_panels().
    """
    widget = widget_class(parent)
    widget.configure(**options)
    colors = {k: v for k, v in options.items() if k in ("bg", "fg")}
    if colors:
        _tk_colors.append((widget, colors))
    return widget


def _alive(widget):
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:          # its Tk application is gone
        return False


def refresh_panels():
    """Redraw live panels (theme changes alter the colour behind their corners)."""
    _panels[:] = [p for p in _panels if _alive(p)]
    for panel in _panels:
        panel.refresh()
    _tk_colors[:] = [(w, c) for w, c in _tk_colors if _alive(w)]
    for widget, colors in _tk_colors:
        widget.configure(**colors)
