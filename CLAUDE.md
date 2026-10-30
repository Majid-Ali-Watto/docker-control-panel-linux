# Docker Control Panel — Claude Code Context

## Project Overview

A Python/Tkinter GUI application for managing Docker on Linux, macOS and Windows. Provides a graphical interface for containers, images, volumes, networks, stats, Compose projects, system info/contexts/events, and Docker service control. On Linux, Docker commands run through sudo (password asked once) unless the user can already reach Docker directly (member of the `docker` group) — then no password is asked at all. On macOS / Windows Docker Desktop runs as the user, so sudo and the password are never used.

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
│   ├── config_manager.py      # Password storage (desktop keyring via secret-tool, else ~/.docker-gui/config.json mode 0600), settings (get_setting/set_setting), theme, compose projects
│   ├── config_menu.py         # Sidebar menu structure — all button wiring lives here
│   ├── config_themes.py       # Theme definitions
│   └── config_tooltips.py     # Tooltip strings for every sidebar and action button
├── docker/
│   ├── actions.py             # Docker service actions (start/stop/restart service, clean all)
│   ├── commands.py            # All docker CLI command strings (single source of truth)
│   └── operations.py          # Core subprocess execution: run_docker_cmd, stream_docker_cmd, show_table_command
├── containers/
│   ├── actions.py             # Bulk container ops (start/stop/restart/delete all)
│   ├── details.py             # format_container_details: readable state/health/restarts/ports/mounts/env from docker inspect JSON (secret-looking env values hidden)
│   ├── dialogs.py             # File browser, container terminal, show_logs_window (shared log viewer: containers + Compose)
│   └── tables.py              # show_all/running/stopped/paused_containers
├── images/
│   ├── actions.py             # Bulk image ops (prune, delete all)
│   ├── dialogs.py             # Pull, push, registry login/logout, search Hub, build (with --platform), load, import, vulnerability scan; pull/build status
│   └── tables.py              # show_images, show_used/unused/dangling_images
├── volumes/
│   ├── actions.py             # Bulk volume ops (prune, delete used/all)
│   ├── dialogs.py             # Create volume dialog
│   └── tables.py              # show_volumes, show_used/unused_volumes
├── networks/
│   ├── actions.py             # Bulk network ops (prune)
│   ├── dialogs.py             # Create network dialog
│   └── tables.py              # show_networks
├── compose/
│   ├── dialogs.py             # Compose up dialog: pick file(s) or a project folder; remembers them
│   └── tables.py              # show_compose_projects (also lists remembered projects as "not running")
├── stats/
│   ├── dialogs.py             # Disk usage view: Images/Containers/Volumes/Build Cache tabs, each a DisplayManager table
│   └── tables.py              # show_containers_with_stats (Live Stats, interval button, CPU/MEM trend sparklines), show_docker_disk_storage_simple
├── system/
│   ├── actions.py             # show_system_info (docker version + info), show_builders (buildx), prune_build_cache
│   ├── dialogs.py             # Live Docker events window (type / since filters, colour-coded, save)
│   └── tables.py              # show_contexts (rows act through the 'context' table type: Use / Inspect)
├── shared/
│   ├── context_menus.py       # Right-click menus for table and text output widgets
│   ├── helpers.py             # Shared formatting / argument-building utilities
│   ├── item_actions.py        # Per-row action buttons — create_selected_item_actions()
│   └── stream.py              # Session tracking for streaming commands (build/pull status)
├── ui/
│   ├── ui_components.py       # Reusable dialogs (password prompt, install prompt, Tooltip)
│   ├── ui_display.py          # DisplayManager — switches between table/text views
│   ├── rounded.py             # Rounded corners: ttk style images + RoundedPanel/RoundedBadge
│   ├── datetime_picker.py     # Calendar + time picker dialog (custom date range From/To)
│   ├── filter_popup.py        # Dropdown under the toolbar's Filters button (Created range, Apply / Clear filters)
│   ├── cell_format.py         # format_cell: display-only tidying (dates, sizes, ports, compose files); status_tone: unhealthy / restarting / non-zero exit → row text colour
│   ├── settings_dialog.py     # Settings: Live Stats interval, container engine, terminal, notifications
│   ├── popup_menu.py          # PopupMenu: padded, bordered, rounded popup used by the table's right-click menu
│   ├── table_cells.py         # CellSelection: active table cell (outline + raw value for copying)
│   ├── landing_page.py        # LandingPage: Docker category home (hero + status, service buttons, category cards)
│   ├── scroll_frame.py        # ScrollFrame: scrolling container (wheel, wrap-to-width labels, theme-aware canvas)
│   ├── terminal_panel.py      # Embedded terminal panel
│   └── keyboard_navigation.py # Keyboard shortcuts and focus management
├── help/
│   ├── help_commands.py       # APP_COMMAND_SECTIONS (generated from docker/commands.py + _DESCRIPTIONS + inline extras) and COMMAND_SECTIONS (general reference); commands_as_text()
│   ├── commands_view.py       # Commands tab: "Used by this app" / "Reference" switch, category dropdown, search, per-row Copy, Copy all / Download (rows built in batches)
│   ├── help_view.py           # Help tab: searchable collapsible cards rendered from help_info.HELP_SECTIONS
│   ├── creator_view.py        # Creator tab: profile card, link cards (Open / Copy), About card with tech chips
│   ├── help_creator.py        # Creator + app data (name, role, links, tagline, tech stack)
│   └── help_info.py           # HELP_SECTIONS (structured help content)
└── utils/
    ├── utils.py               # Docker install/running checks (docker_service_active), engine (docker|podman) swap, docker_needs_sudo, run_cmd (optional stdin input), async_run, notify (notification_command per OS)
    ├── platform_utils.py      # IS_LINUX/IS_MAC/IS_WIN, uses_sudo, prepare_environment (XIM opt-out, DPI, PATH), popen_flags, clean_subprocess_env, service_manager + Docker Desktop control
    ├── shell.py               # Windows only: runs the command strings without a shell (shlex parser: $(...), 2>/dev/null, || true)
    ├── terminals.py           # Terminal emulators per OS: installed_terminals, write_script, launch
    └── threads.py             # Threading helpers for async docker operations
```

Install: `install.sh` (Linux + macOS) and `install.ps1` / `install.bat` (Windows) are the single-command installers. Linux: detects apt/dnf/pacman/zypper, installs python3+tkinter+venv, Docker and a terminal. macOS: Homebrew (bootstrapped), python@3.12 + python-tk@3.12 (the system Tk is 8.5), Docker Desktop cask, an `.app` bundle in `~/Applications`. Windows: winget for Python 3.12 + Docker Desktop, Start Menu shortcut, `docker-gui.cmd` shim in `%LOCALAPPDATA%\Microsoft\WindowsApps`. All build `.venv` from `requirements.txt` (rebuilt if its imports fail). `docker-gui` follows its own symlink by hand (BSD `readlink` has no `-f`) and runs `.venv/bin/python`; `docker-gui.cmd` runs `pythonw`. `install.sh` must stay bash 3.2-safe (macOS): guard empty arrays under `set -u`, no `${var,,}`. `install.ps1` must stay ASCII-only (Windows PowerShell 5.1). New third-party imports must be added to `requirements.txt`.

## Platform layer

Everything OS-specific goes through `src/utils/platform_utils.py` (flags, `uses_sudo()`, `service_manager()` = `systemd` | `desktop` | `None`), `terminals.py` and `shell.py`; other modules never test the OS themselves. Read the flags as `platform_utils.IS_WIN` (module attribute, never `from … import IS_WIN`) so tests switch OS with one patch (`tests/test_platforms.py`). Rules:

- **POSIX (Linux + macOS)** keep `shell=True` with the command strings as written. **Windows** has no POSIX shell: `run_cmd` / `stream_docker_cmd` go through `shell.popen/output`, which `shlex.split`s the string (every argument is already `shlex.quote`d) and supports only `$(...)`, `2>/dev/null` and `|| true`. A new command constant must not need pipes, `&&`, `;` or redirections — `test_every_command_constant_parses_without_a_shell` enforces it.
- **sudo / password** (Linux only): the password UI, keyring and `sudo -S` prefix are skipped when `uses_sudo()` is False.
- **Service buttons**: `docker.actions._run_service_action` — systemctl (Linux), `docker desktop start|stop|restart` with an `open -a` / `osascript` / `taskkill` fallback (macOS / Windows), or an explanation when there is no systemd. Status is `utils.docker_service_active()` (systemd, else `docker info`).
- **Terminals / notifications**: `terminals.write_script` + `launch` (bash script on Linux/macOS `.command`, `.cmd` on Windows); `utils.notification_command` (notify-send / osascript / PowerShell balloon with the text passed through the environment).
- **Tk**: wheel bindings (`<Button-4/5>` only on Linux), `-zoomed` only on Linux, `XMODIFIERS` only on Linux, console windows hidden with `popen_flags()`.


Entry point: `docker_gui_modular.py` — `DockerGUI` class wires everything together.

## Key Architecture Patterns

- **SOC by sidebar category** — each sidebar category (Containers, Images, Volumes, Networks, Compose, Stats) has its own `src/<category>/` directory with `actions.py`, `tables.py`, and `dialogs.py`. Docker service operations live in `src/docker/`. Shared infrastructure lives in `src/shared/`.
- **No top header bar** — the window is split directly into sidebar (left) + main content (right). The sidebar shows the app title and Docker service status at the top.
- **Landing page** — the Docker category opens on `ui/landing_page.LandingPage` (a child of the output container, packed by `DockerGUI.show_category_buttons`): hero with the service status, Start/Stop/Restart/Clean All buttons (the Docker entries of `get_menu_structure()`), and one card per sidebar category that opens it. The Docker toolbar (`btn_frame`) is hidden there (other categories re-show it). Service actions run from the landing (`_landing_action`) set `view_refresh` to `_show_landing`, so their output has a "← Back" button; clicking Docker in the sidebar also returns. Cards are built after first paint.
- **DisplayManager** (`src/ui/ui_display.py`): single object that owns the output area; call `show_table(columns, rows)` or `show_text_output(text)` — never manipulate output widgets directly.
- **Reloadable lists**: `VIEW_BUTTONS` in `config_menu.py` lists the toolbar buttons that switch the visible list. The last one clicked is remembered in `DisplayManager.view_refresh` so row actions can reload the list in place. Add new list buttons there (the toolbar layout itself is a single row of buttons).
- **Table header / filters**: `DisplayManager._build_header` builds the title + count badge, then one toolbar (search, sort dropdown + Asc/Desc, and a "☰ Filters" button) with identically sized controls. The button opens `filter_popup.FilterPopup` under it: "Created" preset, From/To fields (typed `YYYY-MM-DD[ HH:MM]` or the `datetime_picker.py` calendar via "Pick…", shown only for "Custom range"), and Apply / Clear filters; edits only take effect on Apply, and Clear filters also empties the search box. The button is highlighted while any filter is active and only exists for tables with a date column. A column named `CREATED` (docker `{{.CreatedAt}}`, last column — keep row indexes used by `item_actions.py` stable) enables the date filter; Volumes and Compose have none (search only; Esc clears it). Columns are sized from measured text widths.
- **Table cells**: cells are shown through `cell_format.format_cell(column, text)` (readable dates, `388 MB`, de-duplicated ports, `~/` compose paths) and empty ones as `DisplayManager.EMPTY_CELL` ("—"), but `_rows`/`_shown` keep docker's original text: `get_item_values()` (used by `item_actions.py`), sorting and the date filter use it, while search matches either form and copy uses `get_item_texts()` (what is shown, blanks as ''). Add new display tidying to `format_cell`, keyed by column name — never read row data back from the Treeview. `table_cells.CellSelection` tracks the clicked cell (outlined while its row is selected, follows its row across reloads/sorts). `setup_table_context_menu(display_manager, root)` binds right-click (selects the cell/row under the pointer, then opens a `popup_menu.PopupMenu`: copy cell / copy rows / select all rows / the toolbar's row actions / Close menu) plus Ctrl+C (cell, else rows) and Ctrl+A (select all). `PopupMenu` replaces `tk.Menu` because a native menu cannot have padding, a border or rounded corners; it is a `RoundedPanel` placed over the window (corner pixels show the clicked row's colour), entries run only on a left click (wheel / other buttons are ignored), arrows + Enter work, and an outside click or Esc closes it. Double-click runs the details action in `_DOUBLE_CLICK_ACTION`.
- **Row actions**: in `item_actions.py`, state-changing actions use `_run_mutation` (table stays, status bar reports the result, list reloads in place; errors show the output with a "← Back to list" button). Read-only actions (inspect/logs/history) use `_run_output_command`. Buttons are enabled/disabled by selection via `DisplayManager.update_selection_state()` — register new single-row-only actions in `_SINGLE_ROW_ACTIONS` and new buttons in `_ACTION_LAYOUT`.
- **Rounded corners**: Tk has no border-radius. `src/ui/rounded.py` swaps the border element of ttk buttons/entries/comboboxes/label frames for nine-slice images (`apply_rounded_styles`, re-run on every theme change) and provides `RoundedPanel`/`RoundedBadge` (Canvas) for tk surfaces. Create coloured tk widgets with `rounded.make(...)` — ttkbootstrap discards `bg`/`fg` passed to constructors and resets them on theme change; `make` re-applies them. Button/label text is made legible per theme in this module (`readable`, `on_fill`, `readable_color` — WCAG 4.5:1, 3:1 for disabled); use `readable_color(...)` instead of fixed colour names like `"green"`/`"gray"` on theme surfaces. For secondary text use `style="Muted.TLabel"` (defined in `apply_rounded_styles`, ≥4.5:1 on every theme) — ttkbootstrap's `secondary.TLabel` is 1.6:1 on Darkly/Superhero. Keep `_TILE` large: Tk tiles the image centre, and a small centre makes wide widgets take seconds to repaint.
- **Menu wiring**: all sidebar buttons and their lambdas are defined in `src/config/config_menu.py` via `get_menu_structure()`. Add new actions there.
- **Docker commands**: raw CLI strings live in `src/docker/commands.py` (every new `DOCKER_*` constant needs an entry in `help_commands._DESCRIPTIONS`, otherwise the Commands tab test fails; commands issued inline elsewhere go in `_EXTRA_APP_COMMANDS`); execution goes through `src/docker/operations.py`. Do not inline subprocess calls elsewhere.
- **Threading**: long-running docker commands must use the helpers in `threads.py` to avoid blocking the Tkinter main loop.
- **Tabbed tables**: `DisplayManager.show_table(..., tabs={label: callback}, active_tab=label)` draws a tab strip above the title; the Docker Disk Usage view uses it (one `disk_*` table type per tab, so search, sort, count badge and row actions come for free). Row actions accept those types through `_CONTAINER_VIEWS` / `_IMAGE_VIEWS` / `_VOLUME_VIEWS` in `item_actions.py` — only valid because the tab rows start with the same identifying columns. Relative ages (`2 weeks ago`) sort by age.
- **Compose projects**: files picked in "Up From File" are saved to `compose_projects` in `~/.docker-gui/config.json` so a project stays listed (and can be started again) after `compose down`; entries whose files no longer exist are hidden.
- **Password**: asked once, then kept in the desktop keyring (`secret-tool`, libsecret) when installed, else in `~/.docker-gui/config.json` (0600); a legacy file password moves into the keyring on first load. Read via `config_manager.py` — never prompt inline. At startup `docker_needs_sudo()` (`docker info` without sudo) skips the prompt entirely for users in the `docker` group: `run_cmd`/`stream_docker_cmd` only prefix `sudo -S` when a password is set.
- **Engine and settings**: preferences live under `settings` in the config file (`DEFAULT_SETTINGS`; Settings dialog in the sidebar). `engine` (docker|podman) is applied centrally by `utils.apply_engine`, which swaps the leading `docker` of each command at execution time — command constants stay written once and arguments (image names…) are never touched. Podman is experimental (the Docker service buttons/status still use systemd's docker). Secrets go to a command on stdin (`run_cmd(..., input_text=...)`, e.g. `docker login --password-stdin`), never into argv.
- **Logs viewer**: `containers.dialogs.show_logs_window(root, title, save_name, fetch_command, follow_command, timestamps=True)` is the one log window (lines, follow via `stream_docker_cmd`, search, save). Containers and Compose projects only differ in the two command builders.
- **Row status colour**: `DisplayManager._populate` tags rows of any table with a `STATUS` column through `cell_format.status_tone` (`status_bad|warn|ok` foreground tags, set by `apply_status_colors` on every theme change); details, restarts and health come from the Details row action.
- **System category**: `src/system/` (sidebar "System"): Info, Contexts (a `context` table with Use / Inspect row actions), Events (streaming window), Builders, Prune Build Cache. Contexts do not require the local daemon check.
- **Notifications**: `utils.notify` (notify-send / osascript / PowerShell) fires when a build/pull session finishes (`shared/stream.py`), only while the window is unfocused and enabled in Settings.
- **Terminal launch**: `terminals.launch` uses `clean_subprocess_env()` (re-exported by `utils.py`) to strip snap-injected env vars before calling `subprocess.Popen` on Linux, preventing libpthread conflicts.
- **Streaming sessions**: long-running streaming commands (build, pull) use `_start_stream_session` / `_show_stream_session_window` in `src/shared/stream.py` so the user can close the window and reopen the status later via a dedicated sidebar button.

- **Startup speed (XIM)**: `platform_utils.prepare_environment()` (called by `docker_gui_modular.py` before Tk starts, Linux only) sets `XMODIFIERS=@im=none`. With an XIM server (ibus) Tk's `XCreateIC` costs ~90 ms per call, which made first paint ~11 s and every screen slow; `clean_subprocess_env()` strips it for child processes. Keep that call above the first Tk call.
- **Window / landing**: the window opens maximised (`_maximize`: `-zoomed` on Linux, `state('zoomed')` on Windows / macOS). The Docker page opens on the landing page above.

## Coding Conventions

- Python 3.x, no third-party dependencies beyond the stdlib and Tkinter.
- `ttk` widgets preferred over `tk` widgets.
- Fonts: `JetBrains Mono` for monospace output, `Arial` for labels.
- Keep modules in their respective `src/` subdirectory; do not add top-level Python files.
- Do not mock or simulate docker commands — the app shells out to real `docker` (and `sudo` on Linux).
- Never call `os.killpg`, `start_new_session`, `systemctl`, `notify-send`, `secret-tool` or a terminal emulator outside the platform layer / their one module.

## Common Tasks

**Check the Commands tab data**: every command in `help_commands.py` was validated against the installed docker CLI's `--help` (subcommand path + every flag). After editing it, re-check with `docker <subcommand> --help` for new flags; placeholders (`<x>`), `$(...)` and pipes are only checked up to the first docker invocation. Commands that are not `docker …` constants (`trivy`, the registry-config `cat`) live in `_EXTRA_APP_COMMANDS`; `docker scout` and `docker buildx` come from plugins that may not be installed, so their flags could not be checked against `--help` locally.

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

- The sudo password is kept in the desktop keyring when available, else locally with `chmod 0600`; never log or print it. Registry passwords/tokens travel on stdin only and are cleared from the dialog after use.
- All docker commands are constructed from constants, not from raw user input — keep it that way to avoid shell injection.
- `clean_subprocess_env()` must be used when launching external processes from within the app to avoid snap environment pollution.

## Tests

```bash
python3 -m unittest discover -s tests -t . -v
```

`tests/test_platforms.py` (Windows command parser, Docker Desktop control, terminals, notifications, sudo per OS) and `tests/test_buttons.py` (command constants, GUI action wiring) and `tests/test_new_features.py` (settings, keyring/file password storage, engine swap, stdin input, sudo detection, notifications, container details, events, registry, scan, System category, trends) use `unittest.mock` with correct SOC patch targets — no real Docker daemon required. CI (`.github/workflows/ci.yml`) runs `ruff check` (pyflakes errors, see `pyproject.toml`), `compileall` and `python -m unittest discover -s tests -t .` (xvfb on Linux) on Linux, macOS and Windows, plus each installer; the macOS / Windows jobs are `continue-on-error` until first seen green.

The two older modules describe Linux behaviour and pin the platform with `tests.pretend_linux()` in `setUpModule`, so they pass on every CI OS; new OS-specific tests patch `platform_utils` flags instead of relying on the host.

**Patch path rule**: always patch where the name is bound, not where it is defined. For example, `check_docker_running` imported into `src.containers.actions` must be patched as `src.containers.actions.check_docker_running`, not `src.docker.actions.check_docker_running`. `confirm_action_dialog` is a top-level import in `src.shared.item_actions`, so tests for selected-item actions patch `src.shared.item_actions.confirm_action_dialog`.
