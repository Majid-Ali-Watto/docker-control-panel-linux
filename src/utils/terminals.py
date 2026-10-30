"""
Terminals Module
Which terminal emulators exist on this system and how to run a script in one.
"""

import os
import shutil
import subprocess
import tempfile

from src.utils import platform_utils as plat

# Tried in preference order; each takes a window title and a script to run
_TERMINALS = {
    'tilix': lambda t, s: ['tilix', '--title', t, '-e', s],
    'gnome-terminal': lambda t, s: ['gnome-terminal', '--title', t, '--', 'bash', s],
    'ptyxis': lambda t, s: ['ptyxis', '--new-window', '--title', t, '-x', s],             # Fedora 41+, Ubuntu 25.10+
    'kgx': lambda t, s: ['kgx', '-e', s],                                                  # GNOME Console
    'x-terminal-emulator': lambda t, s: ['x-terminal-emulator', '-title', t, '-e', s],
    'xfce4-terminal': lambda t, s: ['xfce4-terminal', '--title', t, '-e', s],
    'konsole': lambda t, s: ['konsole', '-p', f'tabtitle={t}', '-e', s],
    'mate-terminal': lambda t, s: ['mate-terminal', '--title', t, '-e', s],
    'lxterminal': lambda t, s: ['lxterminal', '-t', t, '-e', s],
    'qterminal': lambda t, s: ['qterminal', '-e', s],
    'terminator': lambda t, s: ['terminator', '-T', t, '-x', s],
    'kitty': lambda t, s: ['kitty', '--title', t, s],
    'alacritty': lambda t, s: ['alacritty', '--title', t, '-e', s],
    'wezterm': lambda t, s: ['wezterm', 'start', '--', s],
    'foot': lambda t, s: ['foot', '-T', t, s],
    'urxvt': lambda t, s: ['urxvt', '-title', t, '-e', s],
    'xterm': lambda t, s: ['xterm', '-title', t, '-e', s],
}

# Package that provides a small terminal, per package manager (used by the install hint)
_INSTALL = {
    "apt-get": "sudo apt install xterm", "dnf": "sudo dnf install xterm", "yum": "sudo yum install xterm",
    "pacman": "sudo pacman -S xterm", "zypper": "sudo zypper install xterm", "apk": "sudo apk add xterm",
    "xbps-install": "sudo xbps-install xterm",
}


def known_terminals():
    return list(_TERMINALS)


def installed_terminals():
    """Terminal emulators found on this system, in preference order."""
    return [name for name in _TERMINALS if shutil.which(name)]


def install_hint():
    return _INSTALL.get(plat.package_manager(), "install any terminal emulator (xterm, tilix, konsole, ...)")


def write_script(lines):
    """Write `lines` to an executable temp bash script and return its path. The caller deletes it."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as script:
        script.write("#!/usr/bin/env bash\n" + "\n".join(lines) + "\n")
    os.chmod(script.name, 0o755)
    return script.name


def launch(script, title, preferred=None):
    """Run `script` in a new terminal window, trying the preferred emulator first.
    Returns (True, None) or (False, last error text)."""
    names = installed_terminals()
    names.sort(key=lambda n: n != preferred)    # stable: the Settings choice goes first
    last_error = None
    for name in names:
        try:
            process = subprocess.Popen(_TERMINALS[name](title, script), stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, start_new_session=True,
                                       cwd=os.path.expanduser("~"), env=plat.clean_subprocess_env())
            try:   # an emulator that dies at once (missing display, bad flag) is not a success
                code = process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                return True, None
            if code == 0:
                return True, None
            detail = process.stderr.read().decode("utf-8", errors="ignore")[:100] if process.stderr else ""
            last_error = f"{name}: exited with code {code}" + (f" - {detail}" if detail else "")
        except FileNotFoundError:
            last_error = f"{name}: not found"
        except OSError as exc:
            last_error = f"{name}: {exc}"
    return False, last_error
