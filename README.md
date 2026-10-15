# Docker Control Panel

A graphical Docker manager for Linux — control containers, images, volumes, networks, Compose projects, and live stats without typing docker commands.

## Features

| Category | What you can do |
|---|---|
| 🐳 **Docker** | Start / stop / restart the Docker service, bulk-clean all resources |
| 📦 **Containers** | View, start, stop, restart, pause, rename, inspect, commit, delete, file browser |
| 🖼 **Images** | Pull, push, search Docker Hub, build, load, save, tag, inspect, run, prune, delete |
| 💾 **Volumes** | View, create, inspect, prune, delete used/unused/all |
| 🕸 **Networks** | View, create, inspect, connect, disconnect, prune |
| 🧩 **Compose** | List projects, bring up from file, down, restart, logs, config |
| 📊 **Stats** | Live container resource usage with CPU/memory trends, detailed disk-usage breakdown |
| ⚙ **System** | Engine info, contexts, live events, builders, build-cache prune |
| 💻 **Terminal** | Interactive shell inside any running container (SUDO_ASKPASS, state-checked) |
| 📄 **Logs** | View and follow container logs with optional timestamps |

Other highlights:
- **Search** — filter any table by typing
- **Right-click** — copy cell values or entire rows
- **Themes** — six persisted ttkbootstrap themes (Darkly, Superhero, Solar, Vapor, Cosmo, Flatly)
- **Password manager** — sudo password kept in the desktop keyring (`secret-tool`) when available, else in `~/.docker-gui/config.json` (0600); not asked at all if your user is in the `docker` group
- **Registry login**, container Details / Processes / Changes / Export, image Scan / Import / Dangling, followable Compose logs, desktop notifications and a Settings dialog
- **Sidebar status** — Docker Running ✅ / Stopped ❌ always visible
- **Active category indicator** — theme-coloured accent strip on the active sidebar button
- **Pull / Build status** — close the streaming window and re-open it later via the status button

## Requirements

- Python 3.x with Tkinter (`sudo apt install python3-tk`)
- Docker (`sudo apt install docker.io`)
- A terminal emulator for the Container Terminal feature (`sudo apt install tilix`)
- Sudo access

## Installation

```bash
./install.sh
```

The script checks all requirements, creates a desktop entry, installs the app icon, and adds a `docker-gui` symlink to `~/.local/bin`.

## Running

```bash
# After install
docker-gui

# Directly
python3 docker_gui_modular.py
./docker-gui
```

## Project Layout

```
docker-ui-modular/
├── docker_gui_modular.py        # Entry point — DockerGUI class
├── docker-gui                   # Executable launcher
├── install.sh                   # Desktop integration installer
├── assets/
│   └── docker-icon.svg          # App icon
├── tests/
│   ├── test_buttons.py          # Unit tests: command constants, GUI wiring (no daemon needed)
│   └── test_new_features.py     # Unit tests: settings, keyring, engine, events, registry, System
└── src/
    ├── config/
    │   ├── config_manager.py    # Password / config I/O
    │   ├── config_menu.py       # Sidebar menu + all button wiring
    │   ├── config_themes.py     # Theme colour palettes
    │   └── config_tooltips.py   # Tooltip text for all buttons
    ├── docker/
    │   ├── actions.py           # Docker service actions (start/stop/restart)
    │   ├── commands.py          # All docker CLI command strings (single source)
    │   └── operations.py        # subprocess execution layer
    ├── containers/
    │   ├── actions.py           # Bulk container actions (start/stop/restart/delete all)
    │   ├── details.py           # Readable container details (docker inspect)
    │   ├── dialogs.py           # File browser, terminal, shared logs viewer
    │   └── tables.py            # Container Treeview population
    ├── images/
    │   ├── actions.py           # Bulk image actions (prune, delete all)
    │   ├── dialogs.py           # Pull, push, registry login, search Hub, build, load, import, scan
    │   └── tables.py            # Image Treeview population
    ├── volumes/
    │   ├── actions.py           # Bulk volume actions (prune, delete used/all)
    │   ├── dialogs.py           # Create volume dialog
    │   └── tables.py            # Volume Treeview population
    ├── networks/
    │   ├── actions.py           # Bulk network actions (prune)
    │   ├── dialogs.py           # Create network dialog
    │   └── tables.py            # Network Treeview population
    ├── compose/
    │   ├── dialogs.py           # Compose up-from-file dialog
    │   └── tables.py            # Compose project Treeview population
    ├── stats/
    │   ├── dialogs.py           # Disk usage detail view
    │   └── tables.py            # Stats (live, trends) and disk storage Treeview population
    ├── system/
    │   ├── actions.py           # Info, builders, prune build cache
    │   ├── dialogs.py           # Live events window
    │   └── tables.py            # Docker contexts
    ├── shared/
    │   ├── context_menus.py     # Right-click menus for table and text views
    │   ├── helpers.py           # Shared formatting / argument-building utilities
    │   ├── item_actions.py      # Per-row action buttons (create_selected_item_actions)
    │   └── stream.py            # Session-tracking for streaming commands (build/pull)
    ├── ui/
    │   ├── ui_components.py     # Reusable dialogs (password prompt, install prompt, Tooltip)
    │   ├── ui_display.py        # DisplayManager — owns the output area
    │   ├── settings_dialog.py   # Settings dialog
    │   ├── terminal_panel.py    # Embedded terminal panel
    │   └── keyboard_navigation.py
    ├── help/
    │   ├── help_commands.py     # Commands tab text
    │   ├── help_creator.py      # Creator info
    │   └── help_info.py         # Help tab text
    └── utils/
        ├── utils.py             # Docker detection, env helpers, run_cmd, async_run
        └── threads.py           # Async operation helpers
```

## Adding a New Action Button

1. Add the command string to `src/docker/commands.py`.
2. Implement the function in the appropriate feature module (e.g. `src/containers/actions.py`).
3. Register the button in `src/config/config_menu.py` → `get_menu_structure()`.
4. Add a tooltip entry to `src/config/config_tooltips.py`.

## Adding a New Table View

Follow the pattern in the relevant `tables.py` module:

```python
def show_my_resource(show_table_callback, show_loading_callback):
    if not check_docker_running(): return
    show_table_command(
        MY_COMMAND,
        ["Col1", "Col2"],
        sudo=True, sudo_password=get_sudo_password(),
        table_callback=show_table_callback,
        loading_callback=show_loading_callback,
        table_type='my_resource',
        table_title="My Resources"
    )
```

## Security

- Sudo password stored at `~/.docker-gui/config.json` with `chmod 0600`.
- All docker commands built from constants — user input is never interpolated into shell strings.
- Password is never logged or printed.
- All `run_cmd` calls pass `sudo=True, sudo_password=get_sudo_password()` so every docker command runs under sudo consistently.
- Terminal launch uses a SUDO_ASKPASS helper script (chmod 0700, cleaned up after use) so sudo does not consume the interactive shell's stdin.

## Tests

```bash
python3 -m unittest discover -s tests -t . -v
```

Unit tests cover the command constants, GUI action wiring and the newer features (settings, keyring storage, engine swap, events, registry, System). They use `unittest.mock` — no real Docker daemon required. GitHub Actions runs them (and `ruff check`) on every push.

## Uninstall

```bash
rm ~/.local/share/applications/docker-gui.desktop
rm ~/.local/share/icons/docker-control-panel.svg
rm ~/.local/bin/docker-gui
rm -rf ~/.docker-gui/   # removes saved password/config
update-desktop-database ~/.local/share/applications/
```
