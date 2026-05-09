# AGENTS.md — Docker Control Panel

Instructions for AI coding agents (OpenAI Codex, Codex CLI, and compatible tools).

## What This Project Is

A Python/Tkinter desktop GUI for managing Docker on Linux. Users control containers, images, volumes, Docker service state, and view live stats — all without typing docker commands manually. Requires a saved sudo password.

## How to Run

```bash
python3 docker_gui_modular.py
# or
./docker-gui
```

No package installation needed — stdlib and Tkinter only.

## Repository Structure

```
docker-ui-modular/
├── docker_gui_modular.py        # Main entry point (DockerGUI class)
├── install.sh                   # Desktop integration installer
├── src/
│   ├── config/
│   │   ├── config_manager.py    # Password/config I/O (~/.docker-gui/config.json)
│   │   ├── config_menu.py       # Menu structure + all button-to-function wiring
│   │   └── config_themes.py     # Theme colour palettes
│   ├── docker/
│   │   ├── docker_actions.py    # Bulk container/image/volume actions
│   │   ├── docker_commands_constants.py  # All docker CLI strings (single source)
│   │   ├── docker_gui_features.py        # Pull image / terminal / logs / disk dialogs
│   │   ├── docker_operations.py          # subprocess execution
│   │   └── docker_tables.py             # Treeview population
│   ├── ui/
│   │   ├── ui_components.py     # Dialogs (password prompt, install prompt)
│   │   ├── ui_display.py        # DisplayManager
│   │   └── keyboard_navigation.py
│   ├── help/
│   │   ├── help_commands.py     # Commands tab text
│   │   └── help_info.py         # Help tab text
│   └── utils/
│       ├── utils.py             # check_docker_installed, is_docker_running
│       └── threads.py           # Async operation helpers
```

## Agent Constraints

### Do

- Place new Python modules inside the appropriate `src/` subdirectory.
- Add new docker command strings to `src/docker/docker_commands_constants.py`.
- Execute docker commands only through `src/docker/docker_operations.py`.
- Use `DisplayManager.show_table()` / `DisplayManager.show_text_output()` to update the UI — never access output widgets directly.
- Run blocking docker operations in a thread via `src/utils/threads.py`.
- Register new sidebar actions in `src/config/config_menu.py` → `get_menu_structure()`.
- Use `ttk` widgets; fonts `JetBrains Mono` (monospace output) and `Arial` (labels).

### Do Not

- Add third-party dependencies — stdlib and Tkinter only.
- Create new top-level `.py` files.
- Inline docker CLI strings anywhere outside `docker_commands_constants.py`.
- Call `subprocess` directly from UI or action modules — always go through `docker_operations.py`.
- Log, print, or expose the sudo password.
- Concatenate raw user input into shell command strings (use parameterised constants).

## How to Add a Feature

### New action button

1. Add the docker command template to `docker_commands_constants.py`.
2. Implement the logic function in the relevant `src/docker/` module.
3. Register the button in `src/config/config_menu.py` under the correct category key.

### New table view

Follow the pattern in `src/docker/docker_tables.py`:

```python
def show_my_resource(show_table_fn, show_loading_fn):
    show_loading_fn(True)
    output = run_docker_command(MY_COMMAND)  # from docker_operations
    rows = parse_output(output)
    show_table_fn(["Col1", "Col2"], rows)
    show_loading_fn(False)
```

### New theme

Add an entry to `themes` in `src/config/config_themes.py`:

```python
"My Theme": {
    "ttk_theme": "clam",
    "bg": "#...",
    "text_bg": "#...",
    "text_fg": "#...",
    "button_active": "#...",
    "button_active_fg": "#...",
}
```

## Security Constraints

- Sudo password is stored in `~/.docker-gui/config.json` with mode `0600`.
- All docker commands are built from constant templates — never interpolate unsanitised user input.
- Do not introduce shell=True subprocess calls with user-controlled strings.
