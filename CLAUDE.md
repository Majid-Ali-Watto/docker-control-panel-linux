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
│   ├── dialogs.py             # Compose up dialog: pick file(s) or a project folder; remembers them
│   └── tables.py              # show_compose_projects (also lists remembered projects as "not running")
├── stats/
│   ├── dialogs.py             # Disk usage view: Images/Containers/Volumes/Build Cache tabs, each a DisplayManager table
│   └── tables.py              # show_containers_with_stats, show_docker_disk_storage_simple
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
│   ├── cell_format.py         # format_cell: display-only tidying (dates, sizes, ports, compose files)
│   ├── popup_menu.py          # PopupMenu: padded, bordered, rounded popup used by the table's right-click menu
│   ├── table_cells.py         # CellSelection: active table cell (outline + raw value for copying)
│   ├── landing_page.py        # LandingPage: Docker category home (hero + status, service buttons, category cards)
│   ├── scroll_frame.py        # ScrollFrame: scrolling container (wheel, wrap-to-width labels, theme-aware canvas)
│   ├── terminal_panel.py      # Embedded terminal panel
│   └── keyboard_navigation.py # Keyboard shortcuts and focus management
├── help/
│   ├── help_commands.py       # COMMAND_SECTIONS (single source of the command reference) + commands_as_text()
│   ├── commands_view.py       # Commands tab: searchable list + category chips, per-row Copy, Copy all / Download (rows built in batches)
│   ├── help_view.py           # Help tab: searchable collapsible cards rendered from help_info.HELP_SECTIONS
│   ├── creator_view.py        # Creator tab: profile card, link cards (Open / Copy), About card with tech chips
│   ├── help_creator.py        # Creator + app data (name, role, links, tagline, tech stack)
│   └── help_info.py           # HELP_SECTIONS (structured help content)
└── utils/
    ├── utils.py               # Docker install/running checks, run_cmd, async_run, clean_subprocess_env
    └── threads.py             # Threading helpers for async docker operations
```

Entry point: `docker_gui_modular.py` — `DockerGUI` class wires everything together.

## Key Architecture Patterns

- **SOC by sidebar category** — each sidebar category (Containers, Images, Volumes, Networks, Compose, Stats) has its own `src/<category>/` directory with `actions.py`, `tables.py`, and `dialogs.py`. Docker service operations live in `src/docker/`. Shared infrastructure lives in `src/shared/`.
- **No top header bar** — the window is split directly into sidebar (left) + main content (right). The sidebar shows the app title and Docker service status at the top.
- **Landing page** — the Docker category opens on `ui/landing_page.LandingPage` (a child of the output container, packed by `DockerGUI.show_category_buttons`): hero with the service status, Start/Stop/Restart/Clean All buttons (the Docker entries of `get_menu_structure()`), and one card per sidebar category that opens it. Any view shown through `DisplayManager` hides it; clicking Docker in the sidebar brings it back. Cards are built after first paint.
- **DisplayManager** (`src/ui/ui_display.py`): single object that owns the output area; call `show_table(columns, rows)` or `show_text_output(text)` — never manipulate output widgets directly.
- **Reloadable lists**: `VIEW_BUTTONS` in `config_menu.py` lists the toolbar buttons that switch the visible list. The last one clicked is remembered in `DisplayManager.view_refresh` so row actions can reload the list in place. Add new list buttons there (the toolbar layout itself is a single row of buttons).
- **Table header / filters**: `DisplayManager._build_header` builds the title + count badge, then one toolbar (search, sort dropdown + Asc/Desc, and a "☰ Filters" button) with identically sized controls. The button opens `filter_popup.FilterPopup` under it: "Created" preset, From/To fields (typed `YYYY-MM-DD[ HH:MM]` or the `datetime_picker.py` calendar via "Pick…", shown only for "Custom range"), and Apply / Clear filters; edits only take effect on Apply, and Clear filters also empties the search box. The button is highlighted while any filter is active and only exists for tables with a date column. A column named `CREATED` (docker `{{.CreatedAt}}`, last column — keep row indexes used by `item_actions.py` stable) enables the date filter; Volumes and Compose have none (search only; Esc clears it). Columns are sized from measured text widths.
- **Table cells**: cells are shown through `cell_format.format_cell(column, text)` (readable dates, `388 MB`, de-duplicated ports, `~/` compose paths) and empty ones as `DisplayManager.EMPTY_CELL` ("—"), but `_rows`/`_shown` keep docker's original text: `get_item_values()` (used by `item_actions.py`), sorting and the date filter use it, while search matches either form and copy uses `get_item_texts()` (what is shown, blanks as ''). Add new display tidying to `format_cell`, keyed by column name — never read row data back from the Treeview. `table_cells.CellSelection` tracks the clicked cell (outlined while its row is selected, follows its row across reloads/sorts). `setup_table_context_menu(display_manager, root)` binds right-click (selects the cell/row under the pointer, then opens a `popup_menu.PopupMenu`: copy cell / copy rows / select all rows / the toolbar's row actions / Close menu) plus Ctrl+C (cell, else rows) and Ctrl+A (select all). `PopupMenu` replaces `tk.Menu` because a native menu cannot have padding, a border or rounded corners; it is a `RoundedPanel` placed over the window (corner pixels show the clicked row's colour), entries run only on a left click (wheel / other buttons are ignored), arrows + Enter work, and an outside click or Esc closes it. Double-click runs the details action in `_DOUBLE_CLICK_ACTION`.
- **Row actions**: in `item_actions.py`, state-changing actions use `_run_mutation` (table stays, status bar reports the result, list reloads in place; errors show the output with a "← Back to list" button). Read-only actions (inspect/logs/history) use `_run_output_command`. Buttons are enabled/disabled by selection via `DisplayManager.update_selection_state()` — register new single-row-only actions in `_SINGLE_ROW_ACTIONS` and new buttons in `_ACTION_LAYOUT`.
- **Rounded corners**: Tk has no border-radius. `src/ui/rounded.py` swaps the border element of ttk buttons/entries/comboboxes/label frames for nine-slice images (`apply_rounded_styles`, re-run on every theme change) and provides `RoundedPanel`/`RoundedBadge` (Canvas) for tk surfaces. Create coloured tk widgets with `rounded.make(...)` — ttkbootstrap discards `bg`/`fg` passed to constructors and resets them on theme change; `make` re-applies them. Button/label text is made legible per theme in this module (`readable`, `on_fill`, `readable_color` — WCAG 4.5:1, 3:1 for disabled); use `readable_color(...)` instead of fixed colour names like `"green"`/`"gray"` on theme surfaces. Keep `_TILE` large: Tk tiles the image centre, and a small centre makes wide widgets take seconds to repaint.
- **Menu wiring**: all sidebar buttons and their lambdas are defined in `src/config/config_menu.py` via `get_menu_structure()`. Add new actions there.
- **Docker commands**: raw CLI strings live in `src/docker/commands.py`; execution goes through `src/docker/operations.py`. Do not inline subprocess calls elsewhere.
- **Threading**: long-running docker commands must use the helpers in `threads.py` to avoid blocking the Tkinter main loop.
- **Tabbed tables**: `DisplayManager.show_table(..., tabs={label: callback}, active_tab=label)` draws a tab strip above the title; the Docker Disk Usage view uses it (one `disk_*` table type per tab, so search, sort, count badge and row actions come for free). Row actions accept those types through `_CONTAINER_VIEWS` / `_IMAGE_VIEWS` / `_VOLUME_VIEWS` in `item_actions.py` — only valid because the tab rows start with the same identifying columns. Relative ages (`2 weeks ago`) sort by age.
- **Compose projects**: files picked in "Up From File" are saved to `compose_projects` in `~/.docker-gui/config.json` so a project stays listed (and can be started again) after `compose down`; entries whose files no longer exist are hidden.
- **Password**: stored once in `~/.docker-gui/config.json` (0600). Read via `config_manager.py` — never prompt inline.
- **Terminal launch**: uses `clean_subprocess_env()` from `utils.py` to strip snap-injected env vars before calling `subprocess.Popen`, preventing libpthread conflicts.
- **Streaming sessions**: long-running streaming commands (build, pull) use `_start_stream_session` / `_show_stream_session_window` in `src/shared/stream.py` so the user can close the window and reopen the status later via a dedicated sidebar button.

- **Startup speed (XIM)**: `docker_gui_modular.py` sets `XMODIFIERS=@im=none` before Tk starts. With an XIM server (ibus) Tk's `XCreateIC` costs ~90 ms per call, which made first paint ~11 s and every screen slow; `clean_subprocess_env()` strips it for child processes. Keep that line above the first Tk call.
- **Window / landing**: the window opens maximised (`_maximize`, `-zoomed`). The Docker page opens on the landing page above.

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
