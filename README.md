# Docker Control Panel

A graphical Docker manager for **Linux, macOS and Windows** — control containers, images, volumes, networks, Compose projects, and live stats without typing docker commands.

## Features

| Category | What you can do |
|---|---|
| 🐳 **Docker** | Start / stop / restart the Docker service (systemd on Linux, Docker Desktop on macOS / Windows), bulk-clean all resources |
| 📦 **Containers** | View, start, stop, restart, pause, rename, inspect, commit, delete, file browser |
| 🖼 **Images** | Pull, push, search Docker Hub, build, load, save, tag, inspect, run, prune, delete |
| 💾 **Volumes** | View, create, inspect, prune, delete used/unused/all |
| 🕸 **Networks** | View, create, inspect, connect, disconnect, prune |
| 🧩 **Compose** | List projects, bring up from file, down, restart, logs, config |
| 📊 **Stats** | Live container resource usage with CPU/memory trends, detailed disk-usage breakdown |
| ⚙ **System** | Engine info, contexts, live events, builders, build-cache prune |
| 💻 **Terminal** | Interactive shell inside any running container, opened in your terminal (Linux emulators, Terminal / iTerm, Windows Terminal / cmd) |
| 📄 **Logs** | View and follow container logs with optional timestamps |

Other highlights:
- **Search** — filter any table by typing
- **Right-click** — copy cell values or entire rows
- **Themes** — six persisted ttkbootstrap themes (Darkly, Superhero, Solar, Vapor, Cosmo, Flatly)
- **Password manager** (Linux) — sudo password kept in the desktop keyring (`secret-tool`) when available, else in `~/.docker-gui/config.json` (0600); not asked at all if your user is in the `docker` group, and never on macOS / Windows (Docker Desktop runs as you)
- **Registry login**, container Details / Processes / Changes / Export, image Scan / Import / Dangling, followable Compose logs, desktop notifications and a Settings dialog
- **Sidebar status** — Docker Running ✅ / Stopped ❌ always visible
- **Active category indicator** — theme-coloured accent strip on the active sidebar button
- **Pull / Build status** — close the streaming window and re-open it later via the status button

## Requirements

| | Linux | macOS | Windows |
|---|---|---|---|
| Supported | Ubuntu 22.04+, Debian, Fedora, Arch, openSUSE (`apt` / `dnf` / `pacman` / `zypper`) | 12+ (Intel / Apple silicon) | 10 / 11 (needs `winget`, bundled with current Windows) |
| Docker | Docker Engine (installed for you) | Docker Desktop (installed with Homebrew) | Docker Desktop (installed with winget) |
| Needs | sudo access | an administrator account (Homebrew, Docker Desktop) | — |

Everything else — Python 3.10+ with a Tk 8.6, a terminal emulator, and the Python packages in `requirements.txt` (`ttkbootstrap`, `pillow`) — is installed for you by the installer.

## Installation

One command, no questions asked. Run it again any time: it only does what is missing, and rebuilds a broken `.venv`.

**Linux and macOS**

```bash
./install.sh
```

Installs the system packages (your distro's package manager, asking for your sudo password once; on macOS Homebrew, installed first if missing), builds a private `.venv`, then creates the desktop entry (Linux: Applications menu; macOS: `~/Applications/Docker Control Panel.app`) and a `docker-gui` command in `~/.local/bin`.

**Windows**

```bat
install.bat
```

(or `powershell -ExecutionPolicy Bypass -File install.ps1`). Installs Python 3.12 and Docker Desktop with `winget` if they are missing, builds the `.venv`, adds a Start Menu shortcut and a `docker-gui` command. Docker Desktop may ask you to restart Windows (WSL 2) the first time.

## Running

```bash
docker-gui                  # Linux / macOS / Windows terminal, after installing
./docker-gui                # straight from the project folder (Windows: docker-gui.cmd)
```

Or use the Applications menu / Launchpad / Start menu entry.

## How it differs per platform

| | Linux | macOS / Windows |
|---|---|---|
| Docker commands | through `sudo -S` unless you are in the `docker` group | directly (Docker Desktop runs as you; no password prompt, no password storage) |
| Start / Stop / Restart | `systemctl` (without systemd the buttons explain what to do) | Docker Desktop (`docker desktop …`, or the app itself on older versions) |
| Container terminal | tilix, gnome-terminal, konsole, xterm, … (choose in Settings) | Terminal / iTerm on macOS; Windows Terminal / cmd on Windows |
| Notifications | `notify-send` | `osascript` / a PowerShell balloon |
| Command execution | `/bin/sh` | macOS: `/bin/sh`; Windows: a built-in parser, no shell (`src/utils/shell.py`) |

Podman support is experimental and Linux-oriented.

## Project Layout

```
docker-ui-modular/
├── docker_gui_modular.py        # Entry point — DockerGUI class
├── docker-gui                   # Launcher (Linux / macOS)
├── docker-gui.cmd               # Launcher (Windows, no console window)
├── install.sh / install.ps1     # One-command installers (Linux + macOS / Windows); install.bat double-clicks the latter
├── uninstall.sh / uninstall.ps1 # Matching uninstallers
├── requirements.txt             # Python dependencies installed into .venv
├── assets/
│   └── docker-icon.{svg,png,ico} # App icon (svg: Linux, png: macOS bundle, ico: Windows shortcut)
├── tests/
│   ├── test_buttons.py          # Unit tests: command constants, GUI wiring (no daemon needed)
│   ├── test_new_features.py     # Unit tests: settings, keyring, engine, events, registry, System
│   └── test_platforms.py        # Unit tests: Windows command parser, Docker Desktop control, terminals, notifications
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
        ├── utils.py             # Docker detection, run_cmd, async_run, notifications
        ├── platform_utils.py    # OS flags, sudo/service differences, Docker Desktop control
        ├── shell.py             # Windows: runs command strings without a shell
        ├── terminals.py         # Terminal emulators per OS
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

Unit tests cover the command constants, GUI action wiring and the newer features (settings, keyring storage, engine swap, events, registry, System). They use `unittest.mock` — no real Docker daemon required. GitHub Actions runs them (and `ruff check`) on Linux, macOS and Windows on every push, and also runs each installer.

## Uninstall

```bash
./uninstall.sh          # Linux / macOS: entry, command, icon and .venv
rm -rf ~/.docker-gui/   # also remove saved settings (and the saved password, if the keyring was not used)
```

On Windows run `uninstall.bat` (Start Menu shortcut, `docker-gui` command, `.venv`); settings live in `%USERPROFILE%\.docker-gui`.
