"""
Theme configurations for Docker GUI (powered by ttkbootstrap)

A theme is only a ttkbootstrap theme name. Every other colour (sidebar, text area, table rows,
separators, accents) is derived from that theme's own palette at runtime
(``rounded.surface_palette`` / ``tone_color``), so the plain tk surfaces always match the ttk
widgets around them and a theme looks the same every time it is selected.
"""

# Default theme name used on startup
DEFAULT_THEME = "Darkly"

themes = {
    "Darkly": {"ttkbs_theme": "darkly"},
    "Superhero": {"ttkbs_theme": "superhero"},
    "Solar": {"ttkbs_theme": "solar"},
    "Vapor": {"ttkbs_theme": "vapor"},
    "Cosmo": {"ttkbs_theme": "cosmo"},
    "Flatly": {"ttkbs_theme": "flatly"},
}
