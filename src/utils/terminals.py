"""
Terminals Module
Which terminal emulators exist on this system and how to run a script in one: the Linux emulators,
macOS Terminal / iTerm, and Windows Terminal / the classic console.
"""

import os
import shutil
import subprocess
import tempfile

from src.utils import platform_utils as plat

# Linux emulators, tried in preference order
_LINUX = ['tilix', 'gnome-terminal', 'x-terminal-emulator',
          'xfce4-terminal', 'konsole', 'mate-terminal', 'terminator', 'xterm']


def known_terminals():
    if plat.IS_MAC:
        return ["Terminal", "iTerm"]
    if plat.IS_WIN:
        return ["wt", "cmd"]
    return _LINUX


def is_installed(name):
    if plat.IS_MAC:
        return name == "Terminal" or os.path.isdir("/Applications/iTerm.app")   # Terminal ships with macOS
    if plat.IS_WIN:
        return name == "cmd" or shutil.which("wt") is not None                   # cmd ships with Windows
    return shutil.which(name) is not None


def installed_terminals():
    """Terminal emulators found on this system, in preference order."""
    return [name for name in known_terminals() if is_installed(name)]


def install_hint():
    if plat.IS_MAC:
        return "Terminal.app ships with macOS."
    if plat.IS_WIN:
        return "winget install Microsoft.WindowsTerminal"
    return "sudo apt install tilix  # or xfce4-terminal, gnome-terminal"


def script_suffix():
    return ".cmd" if plat.IS_WIN else ".command" if plat.IS_MAC else ".sh"


def write_script(lines):
    """Write `lines` to an executable temp script for this OS's shell (a bash script with a shebang,
    or a .cmd batch file) and return its path. The caller deletes it."""
    windows = plat.IS_WIN
    # explicit newline: Python would otherwise translate "\n" itself on a Windows host
    with tempfile.NamedTemporaryFile(mode="w", suffix=script_suffix(), delete=False,
                                     newline="\r\n" if windows else "\n") as script:
        if not windows:
            script.write("#!/bin/bash\n")
        script.write("\n".join(lines) + "\n")
    os.chmod(script.name, 0o755)
    return script.name


def _command(name, title, script):
    """(argv, extra Popen kwargs) that open `script` in terminal `name`."""
    if plat.IS_MAC:
        return ["open", "-a", "iTerm" if name == "iTerm" else "Terminal", script], {}
    if plat.IS_WIN:
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010)
        if name == "wt":
            return ["wt", "new-tab", "--title", title, "cmd", "/c", script], {}
        return ["cmd", "/c", script], {"creationflags": flags}
    table = {
        'tilix': ['tilix', '--title', title, '-e', script],
        'gnome-terminal': ['gnome-terminal', '--title', title, '--', 'bash', script],
        'x-terminal-emulator': ['x-terminal-emulator', '-title', title, '-e', script],
        'xfce4-terminal': ['xfce4-terminal', '--title', title, '-e', script],
        'konsole': ['konsole', '-p', f'tabtitle={title}', '-e', script],
        'mate-terminal': ['mate-terminal', '--title', title, '-e', script],
        'terminator': ['terminator', '-T', title, '-x', script],
        'xterm': ['xterm', '-title', title, '-e', script],
    }
    return table[name], {"start_new_session": True, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
                         "cwd": os.path.expanduser("~"), "env": plat.clean_subprocess_env()}


def launch(script, title, preferred=None):
    """Run `script` in a new terminal window, trying the preferred emulator first.
    Returns (True, None) or (False, last error text)."""
    names = installed_terminals()
    names.sort(key=lambda n: n != preferred)    # stable: the Settings choice goes first
    last_error = None
    for name in names:
        argv, kwargs = _command(name, title, script)
        try:
            process = subprocess.Popen(argv, **kwargs)
            if plat.IS_LINUX:
                try:   # an emulator that dies at once (missing display, bad flag) is not a success
                    code = process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    return True, None
                if code != 0:
                    detail = process.stderr.read().decode("utf-8", errors="ignore")[:100] if process.stderr else ""
                    last_error = f"{name}: exited with code {code}" + (f" - {detail}" if detail else "")
                    continue
            return True, None
        except FileNotFoundError:
            last_error = f"{name}: not found"
        except OSError as exc:
            last_error = f"{name}: {exc}"
    return False, last_error
