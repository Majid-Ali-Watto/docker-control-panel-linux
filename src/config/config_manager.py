"""
Configuration Manager Module
Handles application settings, password storage, and configuration management.
"""

import os
import json
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


def load_saved_password():
    """Load saved password from config file"""
    return _load_config().get('password', None)


def has_saved_password():
    """Return whether a saved password exists in config."""
    return bool(load_saved_password())


def save_password(password):
    """Save password to config file"""
    config = _load_config()
    config['password'] = password
    _save_config(config)


def delete_saved_password():
    """Delete saved password"""
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


def get_sudo_password():
    """Get current sudo password"""
    global SUDO_PASSWORD
    return SUDO_PASSWORD


def set_sudo_password(password):
    """Set sudo password"""
    global SUDO_PASSWORD
    SUDO_PASSWORD = password
