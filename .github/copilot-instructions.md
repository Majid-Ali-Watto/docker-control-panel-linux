# GitHub Copilot Instructions

## Project

Docker Control Panel — a Python/Tkinter desktop GUI for managing Docker on Linux (containers, images, volumes, networks, Compose projects, stats, service control). Requires sudo.

## Tech Stack

- **Language**: Python 3.x, stdlib only (ttkbootstrap is the only third-party dep — already installed)
- **UI**: Tkinter + ttk + ttkbootstrap
- **Target OS**: Linux (Ubuntu / Debian)

## Directory Map

| Path | Purpose |
|---|---|
| `docker_gui_modular.py` | Entry point, `DockerGUI` class |
| `src/config/config_manager.py` | Password/config storage (`~/.docker-gui/config.json`) |
| `src/config/config_menu.py` | All sidebar menu buttons and their callbacks |
| `src/config/config_themes.py` | Theme colour palettes |
| `src/config/config_tooltips.py` | Tooltip strings for all buttons |
| `src/docker/docker_actions.py` | High-level actions (bulk start/stop/delete) |
| `src/docker/docker_commands_constants.py` | Docker CLI command strings (single source of truth) |
| `src/docker/docker_gui_features.py` | Dialogs: pull image, container terminal, logs, disk usage |
| `src/docker/docker_operations.py` | subprocess execution layer |
| `src/docker/docker_tables.py` | Populate `ttk.Treeview` with docker resource data |
| `src/ui/ui_components.py` | Reusable dialogs (password, install prompt, Tooltip class) |
| `src/ui/ui_display.py` | `DisplayManager` — owns the output area |
| `src/ui/keyboard_navigation.py` | Keyboard shortcuts |
| `src/help/help_commands.py` | Commands tab reference text |
| `src/help/help_creator.py` | Creator info shown in Creator tab |
| `src/help/help_info.py` | Help tab guide text |
| `src/utils/utils.py` | Docker detection, `clean_subprocess_env` |
| `src/utils/threads.py` | Async threading helpers |

## UI Layout

- **No top header bar** — the window is sidebar (left) + main content (right).
- **Sidebar top**: app title label + Docker status label (`docker_status_var` StringVar).
- **Main content top**: action toolbar (`btn_frame` LabelFrame).
- **Below toolbar**: Docker info panel (visible only when Docker category is active).
- **Below info panel**: output area managed exclusively by `DisplayManager`.
- **Right panel** (Docker category only): tabbed help panel (Creator / Commands / Help).

## Rules for Suggestions

- **DisplayManager** is the single owner of the output area. Use `display_manager.show_table(columns, rows)` or `display_manager.show_text_output(text)` — do not touch output widgets directly.
- **Docker commands** must come from `docker_commands_constants.py`. Never inline raw command strings.
- **subprocess calls** must go through `src/docker/docker_operations.py`.
- **Long-running operations** must run in a thread using helpers in `src/utils/threads.py`.
- **New buttons** → register in `src/config/config_menu.py` + add tooltip in `config_tooltips.py`.
- **No new top-level `.py` files** — place code in the correct `src/` subdirectory.
- **No new third-party imports** — stdlib and Tkinter only (ttkbootstrap already present).
- Use `ttk` widgets over bare `tk` widgets wherever a ttk equivalent exists.
- Fonts: `JetBrains Mono` for monospace/output text, `Arial` for UI labels.
- Never log or print the sudo password. Store/read it only via `config_manager.py`.
- Build docker command strings from constants — never concatenate raw user input into shell commands.
- Use `clean_subprocess_env()` from `utils.py` when spawning external processes (terminals, etc.).

## Patterns to Follow

```python
# Correct: table view
def show_my_resource(show_table_fn, show_loading_fn):
    show_loading_fn(True)
    # ... run docker command via docker_operations ...
    show_table_fn(columns, rows, table_type="my_resource", table_title="My Resources")
    show_loading_fn(False)

# Correct: add a menu button (in config_menu.py → get_menu_structure)
("My Action", lambda: my_action_fn(show_text_fn))

# Correct: docker command constant
MY_COMMAND = "docker inspect {container_id}"

# Correct: launch an external process
import subprocess
from src.utils.utils import clean_subprocess_env
subprocess.Popen(cmd, env=clean_subprocess_env(), start_new_session=True)
```
