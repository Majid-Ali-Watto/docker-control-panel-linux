# GitHub Copilot Instructions

## Project

Docker Control Panel — a Python/Tkinter desktop GUI for managing Docker on Linux (containers, images, volumes, stats, service control). Requires sudo.

## Tech Stack

- **Language**: Python 3.x, stdlib only (no pip dependencies)
- **UI**: Tkinter + ttk
- **Target OS**: Linux (Ubuntu)

## Directory Map

| Path | Purpose |
|------|---------|
| `docker_gui_modular.py` | Entry point, `DockerGUI` class |
| `src/config/config_manager.py` | Password/config storage (`~/.docker-gui/config.json`) |
| `src/config/config_menu.py` | All sidebar menu buttons and their callbacks |
| `src/config/config_themes.py` | Theme colour palettes |
| `src/docker/docker_actions.py` | High-level actions (bulk start/stop/delete) |
| `src/docker/docker_commands_constants.py` | Docker CLI command strings (single source of truth) |
| `src/docker/docker_gui_features.py` | Dialogs: pull image, container terminal, logs, disk usage |
| `src/docker/docker_operations.py` | subprocess execution layer |
| `src/docker/docker_tables.py` | Populate `ttk.Treeview` with docker resource data |
| `src/ui/ui_components.py` | Reusable dialogs (password, install prompt) |
| `src/ui/ui_display.py` | `DisplayManager` — owns the output area |
| `src/ui/keyboard_navigation.py` | Keyboard shortcuts |
| `src/help/` | Static help and commands text |
| `src/utils/` | Docker detection helpers, threading utilities |

## Rules for Suggestions

- **DisplayManager** is the single owner of the output area. Use `display_manager.show_table(columns, rows)` or `display_manager.show_text_output(text)` — do not touch output widgets directly.
- **Docker commands** must come from `docker_commands_constants.py`. Never inline raw command strings.
- **subprocess calls** must go through `src/docker/docker_operations.py`.
- **Long-running operations** (any docker call that may block) must run in a thread using helpers in `src/utils/threads.py`.
- **New buttons** → register in `src/config/config_menu.py` under the correct category.
- **No new top-level `.py` files** — place code in the correct `src/` subdirectory.
- **No third-party imports** — stdlib and Tkinter only.
- Use `ttk` widgets over bare `tk` widgets wherever a ttk equivalent exists.
- Fonts: `JetBrains Mono` for monospace/output text, `Arial` for UI labels.
- Never log or print the sudo password. Store/read it only via `config_manager.py`.
- Build docker command strings from constants — never concatenate raw user input into shell commands.

## Patterns to Follow

```python
# Correct: table view
def show_my_resource(show_table_fn, show_loading_fn):
    show_loading_fn(True)
    # ... run docker command via docker_operations ...
    show_table_fn(columns, rows)
    show_loading_fn(False)

# Correct: add a menu button
# In config_menu.py → get_menu_structure():
("My Action", lambda: my_action_fn(show_text_fn))

# Correct: docker command constant
MY_COMMAND = "docker inspect {container_id}"
```
