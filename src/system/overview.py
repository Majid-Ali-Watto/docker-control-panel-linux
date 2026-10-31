"""
Overview of what the app is talking to: CLI, engine, socket, init system, counts. Feeds the
"How it works" card on the Docker home page.
"""

import re
import shutil

from src.config.config_manager import get_sudo_password
from src.docker.commands import (
    DOCKER_CLIENT_VERSION, DOCKER_CONTEXT_HOST, DOCKER_CONTEXT_SHOW, DOCKER_INFO_SUMMARY,
)
from src.utils import platform_utils as plat
from src.utils.utils import engine, run_cmd

_ERROR = re.compile(r"error|denied|cannot|can't|unknown|usage|not found|no such|template", re.IGNORECASE)


def _value(output):
    """First line of a command's output, or None when it looks like an error message."""
    lines = (output or "").strip().splitlines()
    if not lines or _ERROR.search(lines[0]):
        return None
    return lines[0].strip()


def gather_overview():
    """What the app is using right now. Never raises; anything that cannot be found is None."""
    name = engine()
    password = get_sudo_password()
    info = {
        "engine": name,
        "cli_path": shutil.which(name),
        "access": "sudo" if password else "direct",      # direct: the user is in the docker group
        "init": plat.service_manager(),
        "client_version": None, "server_version": None, "context": None, "host": None,
        "containers": None, "running": None, "images": None, "os": None,
    }
    if not info["cli_path"]:
        return info

    def run(command):
        return _value(run_cmd(command, sudo=True, sudo_password=password))

    info["client_version"] = run(DOCKER_CLIENT_VERSION)
    if name == "docker":            # podman has no daemon and different `info` fields
        info["context"] = run(DOCKER_CONTEXT_SHOW)
        info["host"] = run(DOCKER_CONTEXT_HOST)
        parts = (run(DOCKER_INFO_SUMMARY) or "").split("\t")
        if len(parts) == 4:     # an empty last field (OperatingSystem) loses its tab to strip()
            parts.append("")
        if len(parts) == 5:
            info["server_version"], info["containers"], info["running"], info["images"], info["os"] = parts
    return info
