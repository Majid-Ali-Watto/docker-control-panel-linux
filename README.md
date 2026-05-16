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
| 📊 **Stats** | Live container resource usage, detailed disk-usage breakdown |
| 💻 **Terminal** | Interactive shell inside any running container (SUDO_ASKPASS, state-checked) |
| 📄 **Logs** | View and follow container logs with optional timestamps |

Other highlights:
- **Search** — filter any table by typing
- **Right-click** — copy cell values or entire rows
- **Themes** — six persisted ttkbootstrap themes (Darkly, Superhero, Solar, Vapor, Cosmo, Flatly)
- **Password manager** — sudo password stored securely in `~/.docker-gui/config.json` (0600)
- **Sidebar status** — Docker Running ✅ / Stopped ❌ always visible
- **Active category indicator** — theme-coloured accent strip on the active sidebar button

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
└── src/
    ├── config/
    │   ├── config_manager.py    # Password / config I/O
    │   ├── config_menu.py       # Sidebar menu + all button wiring
    │   ├── config_themes.py     # Theme colour palettes
    │   └── config_tooltips.py   # Tooltip text for all buttons
    ├── docker/
    │   ├── docker_actions.py    # Bulk actions (start/stop/delete all)
    │   ├── docker_commands_constants.py  # All docker CLI strings
    │   ├── docker_gui_features.py        # Dialogs: pull, terminal, logs, disk
    │   ├── docker_operations.py          # subprocess execution layer
    │   └── docker_tables.py             # Treeview population
    ├── ui/
    │   ├── ui_components.py     # Reusable dialogs (password, install)
    │   ├── ui_display.py        # DisplayManager — owns the output area
    │   └── keyboard_navigation.py
    ├── help/
    │   ├── help_commands.py     # Commands tab text
    │   ├── help_creator.py      # Creator info
    │   └── help_info.py         # Help tab text
    └── utils/
        ├── utils.py             # Docker detection, env helpers
        └── threads.py           # Async operation helpers
```

## Adding a New Action Button

1. Add the command string to `src/docker/docker_commands_constants.py`.
2. Implement the function in the appropriate `src/docker/` module.
3. Register the button in `src/config/config_menu.py` → `get_menu_structure()`.

## Security

- Sudo password stored at `~/.docker-gui/config.json` with `chmod 0600`.
- All docker commands built from constants — user input is never interpolated into shell strings.
- Password is never logged or printed.
- All `run_cmd` calls pass `sudo=True, sudo_password=get_sudo_password()` so every docker command runs under sudo consistently.
- Terminal launch uses a SUDO_ASKPASS helper script (chmod 0700, cleaned up after use) so sudo does not consume the interactive shell's stdin.

## Tests

```bash
python3 -m pytest tests/ -v
```

Unit tests live in `tests/test_buttons.py` and cover all 72 constants in `docker_commands_constants.py` plus GUI action wiring. Tests use `unittest.mock` — no real Docker daemon is required.

## Uninstall

```bash
rm ~/.local/share/applications/docker-gui.desktop
rm ~/.local/share/icons/docker-control-panel.svg
rm ~/.local/bin/docker-gui
rm -rf ~/.docker-gui/   # removes saved password/config
update-desktop-database ~/.local/share/applications/
```
