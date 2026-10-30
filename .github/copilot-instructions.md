# GitHub Copilot Instructions

## Project

Docker Control Panel — a Python/Tkinter desktop GUI for managing Docker on **Linux** (containers, images, volumes, networks, Compose projects, stats, system info, service control). Works on any mainstream distribution, Python 3.8+. Docker runs through sudo unless the user is in the `docker` group.

Author: Majid Ali, Full Stack Developer — majidaliqau@gmail.com

## Tech Stack

- **Language**: Python 3.8+, stdlib plus `ttkbootstrap` (pin `<2`) and `pillow` (`requirements.txt`, installed into `.venv`)
- **UI**: Tkinter + ttk + ttkbootstrap
- **Target OS**: Linux only (Debian/Ubuntu, Fedora/RHEL family, Arch, openSUSE, Alpine, Void); init systems systemd, OpenRC, runit, SysV

## Directory Map

| Path | Purpose |
|---|---|
| `docker_gui_modular.py` | Entry point, `DockerGUI` class |
| `install.sh` / `uninstall.sh` | One-command installer / uninstaller (all distros) |
| `src/config/config_manager.py` | Password/config storage (`~/.docker-gui/config.json`) |
| `src/config/config_menu.py` | All sidebar menu buttons and their callbacks |
| `src/config/config_themes.py` | Theme colour palettes (default: Darkly) |
| `src/config/config_tooltips.py` | Tooltip strings for all buttons (sidebar, toolbar, home page) |
| `src/docker/actions.py` | Service start/stop/restart (via the init system), clean all |
| `src/docker/commands.py` | Docker CLI command strings (single source of truth) |
| `src/docker/operations.py` | subprocess execution layer (`run_docker_cmd`, `stream_docker_cmd`) |
| `src/<category>/{actions,tables,dialogs}.py` | Containers, images, volumes, networks, compose, stats, system |
| `src/system/overview.py` | `gather_overview()`: CLI, engine, socket, init, counts for the home page |
| `src/ui/ui_components.py` | Reusable dialogs (password, install prompt, `Tooltip`) |
| `src/ui/ui_display.py` | `DisplayManager` — owns the output area |
| `src/ui/landing_page.py` | Docker home page: hero, service buttons, live card, category cards |
| `src/ui/workflow_view.py` | "How it works" card (app → CLI → engine → resources) |
| `src/ui/keyboard_navigation.py` | Keyboard shortcuts |
| `src/help/help_commands.py` | Commands tab reference text |
| `src/help/help_creator.py` | Creator info (name, role, portfolio, GitHub, email) |
| `src/help/legal.py` | Privacy Policy + Terms text; regenerate `PRIVACY.md` / `TERMS.md` with `python3 -m src.help.legal` |
| `src/ui/legal_view.py` | Privacy / Terms reader and the first-run agreement |
| `src/help/help_info.py` | Help tab guide text |
| `src/utils/utils.py` | Docker detection, `run_cmd`, `docker_service_active`, `notify` |
| `src/utils/platform_utils.py` | Init-system detection and service commands, package manager, `clean_subprocess_env` |
| `src/utils/terminals.py` | Terminal emulators: detect, launch, install hint |
| `src/utils/threads.py` | Async threading helpers |
| `assets/` | `docker-icon.svg` (vector app icon; the installer puts it in the hicolor theme), `docker-icon.png` (256 px, re-render from the SVG), `workflow.svg` |

## UI Layout

- **No top header bar** — the window is sidebar (left) + main content (right).
- **Sidebar top**: app title label + Docker status label (`docker_status_var` StringVar).
- **Docker category** opens on the home page (`LandingPage`): hero with status and Privacy / Terms links, service buttons (all have tooltips), a live "How it works" card, and category cards. First start shows the Privacy Policy + Terms agreement.
- **Other categories**: action toolbar (`btn_frame`) above an output area managed exclusively by `DisplayManager`.
- **Right panel** (Docker category only): tabbed help panel (Creator / Commands / Help).

## Rules for Suggestions

- **DisplayManager** is the single owner of the output area. Use `display_manager.show_table(columns, rows)` or `display_manager.show_text_output(text)` — do not touch output widgets directly.
- **Docker commands** come from `src/docker/commands.py`; every new `DOCKER_*` constant needs a description in `help_commands._DESCRIPTIONS`. Never inline raw command strings.
- **subprocess calls** go through `src/docker/operations.py` / `src/utils/utils.py`.
- **Long-running operations** run in a thread using helpers in `src/utils/threads.py`; hand results back with `widget.after(0, ...)`.
- **New buttons** → register in `src/config/config_menu.py` + add a tooltip in `config_tooltips.py` (home-page buttons too).
- **Linux-generic code**: Python 3.8 syntax (no `str.removeprefix`, no `X | Y` unions); never call `systemctl` directly — use `platform_utils.service_command(action)`; no distro-specific package names in app code (they belong in `install.sh`); terminals are added to `terminals._TERMINALS`; scripts use `#!/usr/bin/env bash`.
- **No Windows / macOS code paths.**
- **Privacy stays truthful**: a change that stores new data or contacts a new server must update `src/help/legal.py` (and bump `LEGAL_VERSION`).
- **No new top-level `.py` files** — place code in the correct `src/` subdirectory.
- Use `ttk` widgets over bare `tk` widgets wherever a ttk equivalent exists.
- Fonts: `JetBrains Mono` for monospace/output text, `Arial` for UI labels.
- Never log or print the sudo password. Store/read it only via `config_manager.py`.
- Build docker command strings from constants — never concatenate raw user input into shell commands (quote with `shlex.quote`).
- Use `clean_subprocess_env()` when spawning external processes (terminals, etc.).
- **Pass `sudo=True, sudo_password=get_sudo_password()` to every `run_cmd` call** — omitting sudo causes silent failures when the user is not in the `docker` group.
- For interactive container terminals use a SUDO_ASKPASS helper script (`chmod 0700`) and `sudo -A` so stdin stays available for the shell.

## Adding a New Theme

Add an entry to `themes` in `src/config/config_themes.py` with **all** required keys:
`ttkbs_theme`, `root_bg`, `sidebar_bg`, `header_bg`, `text_bg`, `text_fg`,
`link_fg`, `tree_odd`, `tree_even`, `tree_border`, `active_style`, `indicator_color`.

- `active_style`: a ttkbootstrap button style string (e.g. `"success.TButton"`) applied to the active sidebar button.
- `indicator_color`: hex colour of the 4-px accent strip beside the active sidebar button.

## Tests

```bash
python3 -m unittest discover -s tests -t . -v    # needs a display (xvfb-run -a on CI)
tests/distro_smoke.sh ubuntu:20.04               # installer on a real distro image (needs docker)
```

Everything is mocked with `unittest.mock` — no live Docker daemon required. Patch where a name is *bound* (e.g. `src.containers.actions.check_docker_running`). CI runs Python 3.8 – 3.13 and 14 distribution images.

## Patterns to Follow

```python
# Correct: table view
def show_my_resource(show_table_callback, show_loading_callback):
    if not check_docker_running(): return
    show_table_command(MY_COMMAND, ["Col1", "Col2"], sudo=True, sudo_password=get_sudo_password(),
                       table_callback=show_table_callback, loading_callback=show_loading_callback,
                       table_type="my_resource", table_title="My Resources")

# Correct: add a menu button (in config_menu.py → get_menu_structure)
("My Action", lambda: my_action_fn(show_text_fn))

# Correct: docker command constant
MY_COMMAND = "docker inspect {container_id}"

# Correct: service control, whatever the init system
command = platform_utils.service_command("restart")     # systemctl / rc-service / service / sv, or None
if command is None: show(platform_utils.no_service_manager_text("restart"))

# Correct: launch an external process
subprocess.Popen(cmd, env=clean_subprocess_env(), start_new_session=True)
```
