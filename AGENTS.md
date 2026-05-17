# AGENTS.md — Docker Control Panel

Instructions for AI coding agents (OpenAI Codex, Codex CLI, and compatible tools).

## What This Project Is

A Python/Tkinter desktop GUI for managing Docker on Linux. Users control containers, images, volumes, networks, Compose projects, and Docker service state — all without typing docker commands manually. Requires a saved sudo password.

## How to Run

```bash
python3 docker_gui_modular.py
# or
./docker-gui
```

No package installation needed — stdlib and Tkinter only (plus ttkbootstrap for theming).

## Repository Structure

```
docker-ui-modular/
├── docker_gui_modular.py        # Main entry point (DockerGUI class)
├── docker-gui                   # Executable launcher
├── install.sh                   # Desktop integration installer
├── assets/
│   └── docker-icon.svg          # App icon (SVG)
├── tests/
│   └── test_buttons.py          # Unit tests (109 tests, no daemon needed)
└── src/
    ├── config/
    │   ├── config_manager.py    # Password/config I/O (~/.docker-gui/config.json)
    │   ├── config_menu.py       # Menu structure + all button-to-function wiring
    │   ├── config_themes.py     # Theme colour palettes
    │   └── config_tooltips.py   # Tooltip text for all buttons
    ├── docker/
    │   ├── actions.py           # Docker service actions (start/stop/restart, clean all)
    │   ├── commands.py          # All docker CLI strings (single source of truth)
    │   └── operations.py        # subprocess execution layer
    ├── containers/
    │   ├── actions.py           # Bulk container ops (start/stop/restart/delete all)
    │   ├── dialogs.py           # File browser, container terminal, logs
    │   └── tables.py            # Container Treeview views
    ├── images/
    │   ├── actions.py           # Bulk image ops (prune, delete all)
    │   ├── dialogs.py           # Pull, push, search Hub, build, load; pull/build status
    │   └── tables.py            # Image Treeview views
    ├── volumes/
    │   ├── actions.py           # Bulk volume ops (prune, delete used/all)
    │   ├── dialogs.py           # Create volume dialog
    │   └── tables.py            # Volume Treeview views
    ├── networks/
    │   ├── actions.py           # Bulk network ops (prune)
    │   ├── dialogs.py           # Create network dialog
    │   └── tables.py            # Network Treeview views
    ├── compose/
    │   ├── dialogs.py           # Compose up-from-file dialog
    │   └── tables.py            # Compose project Treeview views
    ├── stats/
    │   ├── dialogs.py           # Disk usage detail view
    │   └── tables.py            # Stats and disk storage Treeview views
    ├── shared/
    │   ├── context_menus.py     # Right-click menus for table and text views
    │   ├── helpers.py           # Shared formatting / argument-building utilities
    │   ├── item_actions.py      # Per-row action buttons (create_selected_item_actions)
    │   └── stream.py            # Session tracking for streaming commands (build/pull)
    ├── ui/
    │   ├── ui_components.py     # Dialogs (password prompt, install prompt, Tooltip)
    │   ├── ui_display.py        # DisplayManager
    │   ├── terminal_panel.py    # Embedded terminal panel
    │   └── keyboard_navigation.py
    ├── help/
    │   ├── help_commands.py     # Commands tab text
    │   ├── help_creator.py      # Creator details
    │   └── help_info.py         # Help tab text
    └── utils/
        ├── utils.py             # check_docker_installed, run_cmd, async_run, clean_subprocess_env
        └── threads.py           # Async operation helpers
```

## UI Structure

- **No top header bar.** The window is sidebar (left, 210 px) + main content (right).
- **Sidebar top**: app title + Docker status label (bound to `docker_status_var`).
- **Main content**: action toolbar (`btn_frame`) → Docker info panel (Docker category only) → output area.
- **Output area**: `DisplayManager` owns it. Use `show_table()` / `show_text_output()` exclusively.

## Agent Constraints

### Do

- Follow the SOC directory layout: each sidebar category has its own `src/<category>/` directory with `actions.py`, `tables.py`, and `dialogs.py`. Shared infrastructure goes in `src/shared/`.
- Add new docker command strings to `src/docker/commands.py`.
- Execute docker commands only through `src/docker/operations.py` (`run_docker_cmd`, `stream_docker_cmd`, `show_table_command`).
- Use `DisplayManager.show_table()` / `DisplayManager.show_text_output()` to update the UI.
- Run blocking docker operations in a thread via `src/utils/threads.py`.
- Register new sidebar actions in `src/config/config_menu.py` → `get_menu_structure()`.
- Use `ttk` widgets; fonts `JetBrains Mono` (monospace output) and `Arial` (labels).
- Use `clean_subprocess_env()` from `utils.py` when launching external processes.

### Do Not

- Add third-party dependencies — stdlib and Tkinter only (ttkbootstrap is already present).
- Create new top-level `.py` files.
- Inline docker CLI strings anywhere outside `src/docker/commands.py`.
- Call `subprocess` directly from UI or action modules — always go through `operations.py`.
- Log, print, or expose the sudo password.
- Concatenate raw user input into shell command strings.
- Create or re-add a top header bar — the sidebar carries the title and status.

## How to Add a Feature

### New action button

1. Add the docker command template to `src/docker/commands.py`.
2. Implement the logic in the relevant feature module (e.g. `src/containers/actions.py`).
3. Register the button in `src/config/config_menu.py` under the correct category key.
4. Add a tooltip entry in `src/config/config_tooltips.py`.

### New table view

Follow the pattern in the relevant `src/<category>/tables.py`:

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

### New theme

Add an entry to `themes` in `src/config/config_themes.py` with keys:
`ttkbs_theme`, `root_bg`, `sidebar_bg`, `header_bg`, `text_bg`, `text_fg`,
`link_fg`, `tree_odd`, `tree_even`, `tree_border`, `active_style`, `indicator_color`.

`active_style` is a ttkbootstrap button style (e.g. `"success.TButton"`) applied to the active sidebar button.
`indicator_color` is the hex colour of the 4-px accent strip drawn next to that button.

## Security Constraints

- Sudo password is stored in `~/.docker-gui/config.json` with mode `0600`.
- All docker commands are built from constant templates — never interpolate unsanitised user input.
- Do not introduce `shell=True` subprocess calls with user-controlled strings.
- **Every `run_cmd` call must pass `sudo=True, sudo_password=get_sudo_password()`** — omitting sudo causes silent permission failures when the user is not in the `docker` group.
- Terminal launch must use a SUDO_ASKPASS helper (temp script, chmod 0700) and `sudo -A` so the interactive shell's stdin is not consumed by the password prompt.

## Tests

Tests live in `tests/test_buttons.py`. Run with:

```bash
python3 -m unittest tests/test_buttons.py -v
```

No real Docker daemon is needed — all docker calls are mocked with `unittest.mock.patch`.

**Patch path rule**: patch where the name is bound, not where it is defined.
- `check_docker_running` imported into `src.containers.actions` → patch `src.containers.actions.check_docker_running`
- `confirm_action_dialog` is a top-level import in `src.shared.item_actions` → patch `src.shared.item_actions.confirm_action_dialog`
- `startThreadForTask` is used inside `async_run` in `src.utils.utils` → patch `src.utils.utils.startThreadForTask`
