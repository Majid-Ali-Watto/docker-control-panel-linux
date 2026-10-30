

def pretend_linux():
    """Started patchers that make the app behave as on Linux with systemd (sudo, systemctl, notify-send).
    The older test modules describe that behaviour; test_platforms.py covers the other OSes."""
    from unittest.mock import patch
    from src.utils import platform_utils as plat
    patchers = [patch.object(plat, "IS_LINUX", True), patch.object(plat, "IS_MAC", False),
                patch.object(plat, "IS_WIN", False), patch.object(plat, "service_manager", return_value="systemd")]
    for patcher in patchers:
        patcher.start()
    return patchers
