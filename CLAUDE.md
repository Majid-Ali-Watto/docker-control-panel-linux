# Docker Control Panel — Claude Code Context

## Project Overview

A Python/Tkinter GUI application for managing Docker on Linux. Provides a graphical interface for containers, images, volumes, stats, and Docker service control. Requires sudo access for Docker commands.

## Running the Application

```bash
python3 docker_gui_modular.py
# or
./docker-gui
```

## Source Layout

```
src/
├── config/
│   ├── config_manager.py      # Password storage (~/.docker-gui/config.json, mode 0600)
│   ├── config_menu.py         # Sidebar menu structure — all button wiring lives here
│   └── config_themes.py       # Theme definitions (Default, Dark, Light Alt, Classic, Clam Light)
├── docker/
│   ├── docker_actions.py      # High-level actions (start/stop service, bulk container ops)
│   ├── docker_commands_constants.py  # All docker CLI command strings
│   ├── docker_gui_features.py # Dialogs: pull image, terminal, logs, disk usage, context menus
│   ├── docker_operations.py   # Core subprocess execution of docker commands
│   └── docker_tables.py       # Populates Treeview tables with docker resource data
├── ui/
│   ├── ui_components.py       # Reusable dialogs (password prompt, install prompt)
│   ├── ui_display.py          # DisplayManager — switches between table/text views
│   └── keyboard_navigation.py # Keyboard shortcuts and focus management
├── help/
│   ├── help_commands.py       # Text shown in Commands tab
│   └── help_info.py           # Text shown in Help tab
└── utils/
    ├── utils.py               # Docker install/running checks
    └── threads.py             # Threading helpers for async docker operations
```

Entry point: `docker_gui_modular.py` — `DockerGUI` class wires everything together.

## Key Architecture Patterns

- **DisplayManager** (`src/ui/ui_display.py`): single object that owns the output area; call `show_table(columns, rows)` or `show_text_output(text)` — never manipulate output widgets directly.
- **Menu wiring**: all sidebar buttons and their lambdas are defined in `src/config/config_menu.py` via `get_menu_structure()`. Add new actions there.
- **Docker commands**: raw CLI strings live in `docker_commands_constants.py`; execution goes through `docker_operations.py`. Do not inline subprocess calls elsewhere.
- **Threading**: long-running docker commands must use the helpers in `threads.py` to avoid blocking the Tkinter main loop.
- **Password**: stored once in `~/.docker-gui/config.json` (0600). Read via `config_manager.py` — never prompt inline.

## Coding Conventions

- Python 3.x, no third-party dependencies beyond the stdlib and Tkinter.
- `ttk` widgets preferred over `tk` widgets.
- Fonts: `JetBrains Mono` for monospace output, `Arial` for labels.
- Keep modules in their respective `src/` subdirectory; do not add top-level Python files.
- Do not mock or simulate docker commands — the app shells out to real `docker` and `sudo`.

## Common Tasks

**Add a new Docker action button:**
1. Add the command string to `docker_commands_constants.py`.
2. Implement the function in the appropriate `src/docker/` module.
3. Register the button in `src/config/config_menu.py` under the correct category.

**Add a new theme:**
Add an entry to the `themes` dict in `src/config/config_themes.py` — keys: `ttk_theme`, `bg`, `text_bg`, `text_fg`, `button_active`, `button_active_fg`.

**Add a new table view:**
Implement a `show_<resource>` function in `src/docker/docker_tables.py` following the existing pattern (query docker, parse output, call `show_table(columns, rows)`).

## Security Notes

- Sudo password is stored locally with `chmod 0600`; never log or print it.
- All docker commands are constructed from constants, not from raw user input — keep it that way to avoid shell injection.
