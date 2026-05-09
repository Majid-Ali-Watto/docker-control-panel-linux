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


def load_saved_password():
    """Load saved password from config file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('password', None)
        except:
            return None
    return None


def save_password(password):
    """Save password to config file"""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'password': password}, f)
    # Set file permissions to user only
    os.chmod(CONFIG_FILE, 0o600)


def delete_saved_password():
    """Delete saved password"""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def get_sudo_password():
    """Get current sudo password"""
    global SUDO_PASSWORD
    return SUDO_PASSWORD


def set_sudo_password(password):
    """Set sudo password"""
    global SUDO_PASSWORD
    SUDO_PASSWORD = password
