# Docker Control Panel — Claude Code Context

## Project Overview

A Python/Tkinter GUI application for managing Docker on Linux. Provides a graphical interface for containers, images, volumes, networks, stats, Compose projects, and Docker service control. Requires sudo access for Docker commands.

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
│   ├── config_themes.py       # Theme definitions
│   └── config_tooltips.py     # Tooltip strings for every sidebar and action button
├── docker/
│   ├── actions.py             # Docker service actions (start/stop/restart service, clean all)
│   ├── commands.py            # All docker CLI command strings (single source of truth)
│   └── operations.py          # Core subprocess execution: run_docker_cmd, stream_docker_cmd, show_table_command
├── containers/
│   ├── actions.py             # Bulk container ops (start/stop/restart/delete all)
│   ├── dialogs.py             # File browser, container terminal, logs dialogs
│   └── tables.py              # show_all/running/stopped/paused_containers
├── images/
│   ├── actions.py             # Bulk image ops (prune, delete all)
│   ├── dialogs.py             # Pull, push, search Hub, build, load image dialogs; pull/build status
│   └── tables.py              # show_images, show_used/unused_images
├── volumes/
│   ├── actions.py             # Bulk volume ops (prune, delete used/all)
│   ├── dialogs.py             # Create volume dialog
│   └── tables.py              # show_volumes, show_used/unused_volumes
├── networks/
│   ├── actions.py             # Bulk network ops (prune)
│   ├── dialogs.py             # Create network dialog
│   └── tables.py              # show_networks
├── compose/
│   ├── dialogs.py             # Compose up-from-file dialog
│   └── tables.py              # show_compose_projects
├── stats/
│   ├── dialogs.py             # Disk usage detail view
│   └── tables.py              # show_containers_with_stats, show_docker_disk_storage_simple
├── shared/
│   ├── context_menus.py       # Right-click menus for table and text output widgets
│   ├── helpers.py             # Shared formatting / argument-building utilities
│   ├── item_actions.py        # Per-row action buttons — create_selected_item_actions()
│   └── stream.py              # Session tracking for streaming commands (build/pull status)
├── ui/
│   ├── ui_components.py       # Reusable dialogs (password prompt, install prompt, Tooltip)
│   ├── ui_display.py          # DisplayManager — switches between table/text views
│   ├── terminal_panel.py      # Embedded terminal panel
│   └── keyboard_navigation.py # Keyboard shortcuts and focus management
├── help/
│   ├── help_commands.py       # Text shown in Commands tab
│   ├── help_creator.py        # Creator name, links shown in Creator tab
│   └── help_info.py           # Text shown in Help tab
└── utils/
    ├── utils.py               # Docker install/running checks, run_cmd, async_run, clean_subprocess_env
    └── threads.py             # Threading helpers for async docker operations
```

Entry point: `docker_gui_modular.py` — `DockerGUI` class wires everything together.

## Key Architecture Patterns

- **SOC by sidebar category** — each sidebar category (Containers, Images, Volumes, Networks, Compose, Stats) has its own `src/<category>/` directory with `actions.py`, `tables.py`, and `dialogs.py`. Docker service operations live in `src/docker/`. Shared infrastructure lives in `src/shared/`.
- **No top header bar** — the window is split directly into sidebar (left) + main content (right). The sidebar shows the app title and Docker service status at the top.
- **Docker info panel** — a dark banner shown below the action toolbar when the Docker category is active (`DockerGUI._create_docker_info_panel`). Hidden for all other categories.
- **DisplayManager** (`src/ui/ui_display.py`): single object that owns the output area; call `show_table(columns, rows)` or `show_text_output(text)` — never manipulate output widgets directly.
- **Menu wiring**: all sidebar buttons and their lambdas are defined in `src/config/config_menu.py` via `get_menu_structure()`. Add new actions there.
- **Docker commands**: raw CLI strings live in `src/docker/commands.py`; execution goes through `src/docker/operations.py`. Do not inline subprocess calls elsewhere.
- **Threading**: long-running docker commands must use the helpers in `threads.py` to avoid blocking the Tkinter main loop.
- **Password**: stored once in `~/.docker-gui/config.json` (0600). Read via `config_manager.py` — never prompt inline.
- **Terminal launch**: uses `clean_subprocess_env()` from `utils.py` to strip snap-injected env vars before calling `subprocess.Popen`, preventing libpthread conflicts.
- **Streaming sessions**: long-running streaming commands (build, pull) use `_start_stream_session` / `_show_stream_session_window` in `src/shared/stream.py` so the user can close the window and reopen the status later via a dedicated sidebar button.

## Coding Conventions

- Python 3.x, no third-party dependencies beyond the stdlib and Tkinter.
- `ttk` widgets preferred over `tk` widgets.
- Fonts: `JetBrains Mono` for monospace output, `Arial` for labels.
- Keep modules in their respective `src/` subdirectory; do not add top-level Python files.
- Do not mock or simulate docker commands — the app shells out to real `docker` and `sudo`.

## Common Tasks

**Add a new Docker action button:**
1. Add the command string to `src/docker/commands.py`.
2. Implement the function in the appropriate feature module (e.g. `src/containers/actions.py`).
3. Register the button in `src/config/config_menu.py` under the correct category.
4. Add a tooltip entry in `src/config/config_tooltips.py`.

**Add a new table view:**
Implement a `show_<resource>` function in the relevant `src/<category>/tables.py` following the existing pattern (check docker running, call `show_table_command` or `async_run`, call `show_table_callback`).

**Add a new theme:**
Add an entry to the `themes` dict in `src/config/config_themes.py`.

## Security Notes

- Sudo password is stored locally with `chmod 0600`; never log or print it.
- All docker commands are constructed from constants, not from raw user input — keep it that way to avoid shell injection.
- `clean_subprocess_env()` must be used when launching external processes from within the app to avoid snap environment pollution.

## Tests

```bash
python3 -m unittest tests/test_buttons.py -v
```

109 unit tests in `tests/test_buttons.py` cover all command constants and GUI action wiring. Uses `unittest.mock` with correct SOC patch targets — no real Docker daemon required.

**Patch path rule**: always patch where the name is bound, not where it is defined. For example, `check_docker_running` imported into `src.containers.actions` must be patched as `src.containers.actions.check_docker_running`, not `src.docker.actions.check_docker_running`. `confirm_action_dialog` is a top-level import in `src.shared.item_actions`, so tests for selected-item actions patch `src.shared.item_actions.confirm_action_dialog`.
