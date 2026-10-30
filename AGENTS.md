# AGENTS.md — Docker Control Panel

Instructions for AI coding agents (OpenAI Codex, Codex CLI, and compatible tools).

## What This Project Is

A Python/Tkinter desktop GUI for managing Docker on **Linux (any distribution, Python 3.8+)**. Users control containers, images, volumes, networks, Compose projects, and Docker service state — all without typing docker commands manually. Docker runs through sudo with a saved password, unless the user is in the `docker` group (then no password is needed). Author: Majid Ali, Full Stack Developer (majidaliqau@gmail.com).

## How to Run

```bash
./install.sh            # once: system packages, Docker, .venv, desktop entry (any distro)
./docker-gui            # or: docker-gui, or the Applications menu entry
```

Python dependencies are `ttkbootstrap` (pinned `<2`: 2.x breaks the rounded styling) and `pillow` (`requirements.txt`, installed into `.venv` by the installer); everything else is the standard library and Tkinter.

## Repository Structure

```
docker-ui-modular/
├── docker_gui_modular.py        # Main entry point (DockerGUI class)
├── docker-gui                   # Launcher (plain POSIX sh)
├── install.sh / uninstall.sh    # One-command installer for every mainstream distro / uninstaller
├── requirements.txt             # ttkbootstrap, pillow (installed into .venv)
├── PRIVACY.md / TERMS.md        # Generated from src/help/legal.py (python3 -m src.help.legal)
├── assets/
│   ├── docker-icon.svg          # App icon, vector (installed to the hicolor icon theme; README)
│   ├── docker-icon.png          # Same icon, 256 px (window icon, home-page hero) — re-render from the SVG when it changes
│   └── workflow.svg             # "How it works" diagram (README)
├── tests/
│   ├── test_buttons.py          # Unit tests: command constants and GUI wiring (no daemon needed)
│   ├── test_new_features.py     # Unit tests: settings, keyring storage, engine, events, registry, System category
│   ├── test_linux_compat.py     # Unit tests: init systems, service buttons, status, terminals, Python 3.8
│   ├── test_home_page.py        # Unit tests: "How it works" card, home tooltips, creator details, images
│   ├── test_legal.py            # Unit tests: Privacy / Terms text, first-run acceptance, reader, home links
│   └── distro_smoke.sh          # Runs the installer on real distro images (needs docker; used by CI)
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
    │   ├── details.py           # Readable container details from docker inspect
    │   ├── dialogs.py           # File browser, container terminal, shared logs viewer
    │   └── tables.py            # Container Treeview views
    ├── images/
    │   ├── actions.py           # Bulk image ops (prune, delete all)
    │   ├── dialogs.py           # Pull, push, registry login, search Hub, build, load, import, scan; pull/build status
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
    │   └── tables.py            # Stats (live, trends) and disk storage Treeview views
    ├── system/
    │   ├── actions.py           # Info, builders, prune build cache
    │   ├── dialogs.py           # Live events window
    │   ├── overview.py          # gather_overview(): CLI, engine, socket, init, counts (home-page card)
    │   └── tables.py            # Docker contexts
    ├── shared/
    │   ├── context_menus.py     # Right-click menus for table and text views
    │   ├── helpers.py           # Shared formatting / argument-building utilities
    │   ├── item_actions.py      # Per-row action buttons (create_selected_item_actions)
    │   └── stream.py            # Session tracking for streaming commands (build/pull)
    ├── ui/
    │   ├── ui_components.py     # Dialogs (password prompt, install prompt, Tooltip)
    │   ├── ui_display.py        # DisplayManager
    │   ├── landing_page.py      # Docker home page (hero, service buttons with tooltips, live card, category cards)
    │   ├── workflow_view.py     # "How it works" canvas card: app → CLI → engine → resources
    │   ├── legal_view.py        # Privacy / Terms reader dialog + first-run agreement
    │   ├── settings_dialog.py   # Settings dialog
    │   ├── terminal_panel.py    # Embedded terminal panel
    │   └── keyboard_navigation.py
    ├── help/
    │   ├── help_commands.py     # Commands tab text
    │   ├── help_creator.py      # Creator details (name, role, portfolio, GitHub, email)
    │   ├── legal.py             # Privacy Policy + Terms text (source of the app pages and the .md files)
    │   └── help_info.py         # Help tab text
    └── utils/
        ├── utils.py             # check_docker_installed, run_cmd, async_run, docker_service_active, notify
        ├── platform_utils.py    # service_manager (systemd/openrc/runit/sysv), service_command, package_manager, clean_subprocess_env
        ├── terminals.py         # 17 terminal emulators: installed_terminals, write_script, launch
        └── threads.py           # Async operation helpers
```

## UI Structure

- **No top header bar.** The window is sidebar (left, 210 px) + main content (right).
- **Sidebar top**: app title + Docker status label (bound to `docker_status_var`).
- **Main content**: action toolbar (`btn_frame`) → output area. The Docker category opens on the **home page** (`ui/landing_page.py`): hero + status, service buttons (Start / Stop / Restart / Clean All, all with tooltips), a live **"How it works"** card (`ui/workflow_view.py`, data from `system/overview.py`), and category cards.
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
- Keep it **Linux-generic**: Python 3.8 syntax and stdlib (no `str.removeprefix`, no `X | Y` unions); never call `systemctl` directly — use `platform_utils.service_command()`; no distro-specific package names or paths in app code (those belong in `install.sh`); new terminal emulators go in `terminals._TERMINALS`.
- Give every new button a tooltip (`src/config/config_tooltips.py`), including home-page buttons.
- Keep the Privacy Policy truthful: if a change stores new data or contacts a new server, update `src/help/legal.py`, bump `LEGAL_VERSION`, and run `python3 -m src.help.legal` to regenerate `PRIVACY.md` / `TERMS.md`.
- Add every new `DOCKER_*` constant to `help_commands._DESCRIPTIONS`.

### Do Not

- Add third-party dependencies beyond `ttkbootstrap` and `pillow` (if you must, add it to `requirements.txt`).
- Add Windows or macOS code paths — the project is Linux-only.
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
- Scripts written to disk use `#!/usr/bin/env bash` (not every distro has `/bin/bash`).

## Tests

```bash
python3 -m unittest discover -s tests -t . -v     # needs a display (xvfb-run -a on CI)
tests/distro_smoke.sh ubuntu:20.04 fedora:latest  # the installer on real distro images (needs docker)
```

No real Docker daemon is needed — all docker calls are mocked with `unittest.mock.patch`. CI runs the suite on Python 3.8 – 3.13 and the installer on 14 distribution images.

**Patch path rule**: patch where the name is bound, not where it is defined.
- `check_docker_running` imported into `src.containers.actions` → patch `src.containers.actions.check_docker_running`
- `confirm_action_dialog` is a top-level import in `src.shared.item_actions` → patch `src.shared.item_actions.confirm_action_dialog`
- `startThreadForTask` is used inside `async_run` in `src.utils.utils` → patch `src.utils.utils.startThreadForTask`
