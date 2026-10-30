"""
Platform Module
Everything that differs between Linux, macOS and Windows lives here (and in shell.py /
terminals.py), so the rest of the app stays platform-agnostic: it asks `uses_sudo()`,
`service_manager()` ... instead of testing the OS itself.

Always read the flags as `platform_utils.IS_WIN` (module attribute) rather than importing the
name, so tests can switch platform with a single patch.
"""

import os
import shutil
import subprocess
import sys

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_LINUX = not IS_WIN and not IS_MAC

# Where Docker's CLI lives when a GUI app was started from the desktop and inherited a minimal PATH
# (Finder / Start menu do not read the shell profile, so Homebrew's and Docker Desktop's bins are missing).
_MAC_PATHS = ["/usr/local/bin", "/opt/homebrew/bin", "~/.docker/bin",
              "/Applications/Docker.app/Contents/Resources/bin"]
_WIN_PATHS = [r"%ProgramFiles%\Docker\Docker\resources\bin", r"%ProgramFiles%\Docker\cli-plugins",
              r"%LOCALAPPDATA%\Microsoft\WinGet\Links"]

DOCKER_DESKTOP_URL = "https://www.docker.com/products/docker-desktop/"


def uses_sudo():
    """True where Docker is a root-owned system service reached through sudo (Linux). Docker Desktop
    on macOS / Windows runs as the user, so no password is ever asked or stored there."""
    return IS_LINUX


def prepare_environment():
    """One-time process setup that must happen before Tk starts."""
    if IS_LINUX:
        # Tk creates an X input-method context (XCreateIC) for many widgets, and with an XIM server
        # such as ibus (XMODIFIERS=@im=ibus) every one is a ~90 ms round trip: ~11 s to first paint
        # and slow screens. This panel needs no input-method composition, so opt out.
        os.environ["XMODIFIERS"] = "@im=none"
    if IS_WIN:
        try:   # crisp text on high-DPI screens instead of bitmap-scaled blur
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    _extend_path()


def _extend_path():
    wanted = _MAC_PATHS if IS_MAC else _WIN_PATHS if IS_WIN else []
    current = os.environ.get("PATH", "").split(os.pathsep)
    extra = [p for p in (os.path.expandvars(os.path.expanduser(w)) for w in wanted)
             if os.path.isdir(p) and p not in current]
    if extra:
        os.environ["PATH"] = os.pathsep.join(current + extra)


def venv_site_packages_globs():
    """Patterns for the project's .venv site-packages (the layout differs on Windows)."""
    return [os.path.join(".venv", "Lib", "site-packages") if IS_WIN
            else os.path.join(".venv", "lib", "python*", "site-packages")]


def popen_flags(new_group=False):
    """subprocess kwargs that keep Windows from flashing a console window for background commands
    (and put a streamed command in its own process group so it can be cancelled). Empty elsewhere."""
    if not IS_WIN:
        return {}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    if new_group:
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    return {"creationflags": flags}


def clean_subprocess_env():
    """Return os.environ with snap-injected overrides stripped.

    When the app runs inside VS Code (snap), GTK/GIO/GDK vars point at
    snap-internal paths that break system binaries like tilix/gnome-terminal
    with a libpthread symbol error.  Removing them lets each binary find its
    own runtime libraries from the system prefix.
    """
    _DROP = {
        'GDK_PIXBUF_MODULEDIR', 'GDK_PIXBUF_MODULE_FILE',
        'GIO_MODULE_DIR', 'GSETTINGS_SCHEMA_DIR',
        'GTK_EXE_PREFIX', 'GTK_IM_MODULE_FILE', 'GTK_PATH',
        'LOCPATH', 'GIO_LAUNCHED_DESKTOP_FILE',
    }
    env = {k: v for k, v in os.environ.items()
           if k not in _DROP and 'SNAP' not in k}
    # The app opts out of X input methods for itself; child programs should not inherit that
    if env.get('XMODIFIERS') == '@im=none':
        del env['XMODIFIERS']
    # Strip snap dirs from PATH
    env['PATH'] = os.pathsep.join(
        p for p in env.get('PATH', '').split(os.pathsep) if '/snap/' not in p
    ) or ('/usr/bin:/usr/local/bin:/bin' if not IS_WIN else '')
    return env


# ── Docker service ──────────────────────────────────────────────────────────

def service_manager():
    """How the Docker daemon is controlled here: 'systemd' (Linux with systemctl), 'desktop' (Docker
    Desktop on macOS / Windows) or None (no known way: WSL, Alpine, ...; then only its status is shown)."""
    if IS_LINUX:
        return "systemd" if shutil.which("systemctl") else None
    return "desktop"


def _run(argv, timeout):
    """(returncode, combined output) of a short helper command; never raises."""
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, **popen_flags())
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return result.returncode, (result.stdout + result.stderr).strip()


def _docker_desktop_exe():
    root = os.environ.get("ProgramFiles", r"C:\Program Files")
    path = os.path.join(root, "Docker", "Docker", "Docker Desktop.exe")
    return path if os.path.exists(path) else None


def _start_desktop_app():
    if IS_MAC:
        return _run(["open", "-a", "Docker"], 30)
    exe = _docker_desktop_exe()
    if not exe:
        return 1, "Docker Desktop.exe was not found - is Docker Desktop installed?"
    try:
        subprocess.Popen([exe], close_fds=True, **popen_flags())
    except OSError as exc:
        return 1, str(exc)
    return 0, "Docker Desktop is starting."


def _stop_desktop_app():
    if IS_MAC:
        return _run(["osascript", "-e", 'quit app "Docker"'], 30)
    return _run(["taskkill", "/F", "/IM", "Docker Desktop.exe"], 30)


def docker_desktop_action(action):
    """Start / stop / restart Docker Desktop (macOS, Windows); a short result text.

    Docker Desktop 4.37+ ships `docker desktop start|stop|restart`, which waits until the engine is
    ready; older versions are driven through the OS (open -a / osascript / taskkill)."""
    code, output = _run(["docker", "desktop", action], 300)
    if code == 0:
        return output or f"Docker Desktop {action}: done."
    steps = {"start": [_start_desktop_app], "stop": [_stop_desktop_app],
             "restart": [_stop_desktop_app, _start_desktop_app]}[action]
    for step in steps:
        code, output = step()
        if code != 0:
            return output or f"Docker Desktop {action} failed."
    return output or f"Docker Desktop {action}: requested."


def no_service_manager_text(action):
    return (f"Cannot {action} Docker from here: this system has no systemd, so start or stop the "
            "daemon with its own init system (for example: sudo service docker start).")
