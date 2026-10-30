"""
Platform Module
How this Linux system differs from the next one: the environment the app starts in, and which init
system controls the Docker daemon (systemd, OpenRC, runit, SysV). The rest of the app asks here
instead of assuming systemd.
"""

import os
import shutil

# Package managers the installer and hints know about, in the order they are looked for
PACKAGE_MANAGERS = ("apt-get", "dnf", "yum", "pacman", "zypper", "apk", "xbps-install")


def prepare_environment():
    """One-time process setup that must happen before Tk starts."""
    # Tk creates an X input-method context (XCreateIC) for many widgets, and with an XIM server
    # such as ibus (XMODIFIERS=@im=ibus) every one is a ~90 ms round trip: ~11 s to first paint
    # and slow screens. This panel needs no input-method composition, so opt out.
    os.environ["XMODIFIERS"] = "@im=none"


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
    env['PATH'] = ':'.join(
        p for p in env.get('PATH', '').split(':') if '/snap/' not in p
    ) or '/usr/bin:/usr/local/bin:/bin'
    return env


def package_manager():
    """The first known package manager on this system (e.g. 'apt-get'), or None."""
    return next((pm for pm in PACKAGE_MANAGERS if shutil.which(pm)), None)


# ── Docker service ──────────────────────────────────────────────────────────

def service_manager():
    """The init system that controls the Docker daemon: 'systemd', 'openrc' (Alpine, Gentoo),
    'runit' (Void), 'sysv' (`service`, e.g. Debian with sysvinit, MX, Devuan) or None when there is
    no known way (WSL1, containers: then only the status is shown)."""
    if os.path.isdir("/run/systemd/system"):     # what sd_booted() checks: systemd is PID 1
        return "systemd"
    if shutil.which("rc-service"):
        return "openrc"
    if shutil.which("sv") and (os.path.isdir("/var/service") or os.path.isdir("/etc/runit")):
        return "runit"
    if shutil.which("service"):
        return "sysv"
    return None


_COMMANDS = {
    "systemd": "systemctl {action} docker.socket docker.service",
    "openrc": "rc-service docker {action}",
    "sysv": "service docker {action}",
    "runit": "sv {verb} docker",
}
_RUNIT_VERBS = {"start": "up", "stop": "down", "restart": "restart"}


def service_command(action):
    """Shell command that starts / stops / restarts the Docker daemon here, or None."""
    template = _COMMANDS.get(service_manager())
    if template is None:
        return None
    return template.format(action=action, verb=_RUNIT_VERBS[action])


def no_service_manager_text(action):
    return (f"Cannot {action} Docker from here: no init system was found (systemd, OpenRC, runit or "
            "SysV), so start or stop the daemon yourself (for example: sudo dockerd).")
