"""
Configuration Manager Module
Handles application settings, password storage, and configuration management.
"""

import os
import json
import shutil
import subprocess
from pathlib import Path

# Configuration constants
CONFIG_DIR = Path.home() / ".docker-gui"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Global password variable (set by main application)
SUDO_PASSWORD = None


def _load_config():
    """Load the full config dictionary from disk."""
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config if isinstance(config, dict) else {}
    except Exception:
        return {}


def _save_config(config):
    """Persist the full config dictionary to disk."""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    os.chmod(CONFIG_FILE, 0o600)


# The sudo password lives in the desktop keyring (libsecret's `secret-tool`) when one is available;
# only without it does it fall back to the 0600 config file.
_KEYRING_ATTRS = ["service", "docker-gui", "kind", "sudo-password"]


def keyring_available():
    """True when `secret-tool` (libsecret) is installed."""
    return shutil.which("secret-tool") is not None


def _keyring(*args, input_text=None):
    """Run secret-tool; (success, stdout). Failure covers a missing tool, a locked or absent keyring."""
    if not keyring_available():
        return False, ""
    try:
        result = subprocess.run(["secret-tool", *args], input=input_text, capture_output=True,
                                text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return False, ""
    return result.returncode == 0, result.stdout


def _keyring_get():
    ok, out = _keyring("lookup", *_KEYRING_ATTRS)
    return out.rstrip("\n") or None if ok else None


def _keyring_set(password):
    return _keyring("store", "--label=Docker Control Panel sudo password", *_KEYRING_ATTRS,
                    input_text=password)[0]


def _drop_file_password():
    config = _load_config()
    if config.pop('password', None) is not None:
        _save_config(config)


def password_storage():
    """Where a saved password would be kept: 'keyring' or 'file'."""
    return "keyring" if keyring_available() else "file"


def load_saved_password():
    """Saved password: from the keyring, else (legacy) from the config file. A file password is
    moved into the keyring as soon as one is available."""
    stored = _keyring_get()
    if stored:
        return stored
    legacy = _load_config().get('password', None)
    if legacy and _keyring_set(legacy):
        _drop_file_password()
    return legacy


def has_saved_password():
    """Return whether a saved password exists."""
    return bool(load_saved_password())


def save_password(password):
    """Save the password in the keyring, or in the config file when there is no keyring."""
    if _keyring_set(password):
        _drop_file_password()
        return
    config = _load_config()
    config['password'] = password
    _save_config(config)


def delete_saved_password():
    """Delete the saved password everywhere it may be stored."""
    _keyring("clear", *_KEYRING_ATTRS)
    config = _load_config()
    config.pop('password', None)

    if config:
        _save_config(config)
    elif CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def load_selected_theme():
    """Load the saved theme name from config file."""
    return _load_config().get('theme', None)


def save_selected_theme(theme_name):
    """Save the selected theme name to config file."""
    config = _load_config()
    config['theme'] = theme_name
    _save_config(config)


# User preferences (Settings dialog), stored under "settings" in the config file
DEFAULT_SETTINGS = {
    "stats_interval": 2,       # seconds between Live Stats refreshes
    "engine": "docker",        # container CLI the app runs: docker | podman
    "notifications": True,     # desktop notice when a build / pull finishes in the background
    "terminal": "auto",        # terminal emulator for the container terminal ("auto": first installed)
}


def get_setting(key):
    """A preference, falling back to its default when unset or of the wrong type."""
    default = DEFAULT_SETTINGS[key]
    settings = _load_config().get('settings')
    value = settings.get(key, default) if isinstance(settings, dict) else default
    return value if isinstance(value, type(default)) else default


def set_setting(key, value):
    """Persist one preference."""
    if key not in DEFAULT_SETTINGS:
        raise KeyError(key)
    config = _load_config()
    if not isinstance(config.get('settings'), dict):
        config['settings'] = {}
    config['settings'][key] = value
    _save_config(config)


def load_compose_projects():
    """Compose file lists the user has started from the app (one list of paths each), oldest first."""
    projects = _load_config().get('compose_projects', [])
    return [files for files in projects
            if isinstance(files, list) and files and all(isinstance(f, str) for f in files)]


def save_compose_project(files):
    """Remember a compose project's files so it stays listed after `compose down`."""
    config = _load_config()
    config['compose_projects'] = [p for p in load_compose_projects() if p != files] + [list(files)]
    _save_config(config)


def get_sudo_password():
    """Get current sudo password"""
    global SUDO_PASSWORD
    return SUDO_PASSWORD


def set_sudo_password(password):
    """Set sudo password"""
    global SUDO_PASSWORD
    SUDO_PASSWORD = password
