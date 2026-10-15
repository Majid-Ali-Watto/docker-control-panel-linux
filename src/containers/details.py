"""
Readable container details built from `docker inspect` JSON: state, health, restarts, ports,
networks, mounts and environment.
"""

import json

_NO_TIME = "0001-01-01T00:00:00Z"
_SECRET_WORDS = ("PASSWORD", "PASSWD", "SECRET", "TOKEN", "PRIVATE_KEY", "API_KEY", "APIKEY", "CREDENTIAL")


def _yes_no(value):
    return "yes" if value else "no"


def _when(value):
    return "—" if not value or value == _NO_TIME else str(value)


def _section(title, lines):
    return [""] + [title] + [f"  {line}" for line in lines] if lines else []


def _environment(config):
    """KEY=value lines; values of secret-looking variables are hidden (Inspect shows them raw)."""
    lines = []
    for entry in config.get("Env") or []:
        key, sep, value = str(entry).partition("=")
        hidden = sep and value and any(word in key.upper() for word in _SECRET_WORDS)
        lines.append(f"{key}=••••••••" if hidden else str(entry))
    return lines


def _ports(data):
    lines = []
    for container_port, bindings in sorted((data.get("NetworkSettings", {}).get("Ports") or {}).items()):
        if not bindings:
            lines.append(f"{container_port}  (not published)")
            continue
        for bind in bindings:
            host = bind.get("HostIp") or "0.0.0.0"
            lines.append(f"{container_port}  →  {host}:{bind.get('HostPort', '')}")
    return lines


def _networks(data):
    return [f"{name:<24}{info.get('IPAddress') or '—'}"
            for name, info in sorted((data.get("NetworkSettings", {}).get("Networks") or {}).items())]


def _mounts(data):
    lines = []
    for mount in data.get("Mounts") or []:
        source = mount.get("Name") or mount.get("Source") or "—"
        mode = "rw" if mount.get("RW", True) else "ro"
        lines.append(f"{mount.get('Type', ''):<7}{source}  →  {mount.get('Destination', '')}  ({mode})")
    return lines


def format_container_details(inspect_text):
    """Details of the container in `docker inspect` output as plain text. Anything that is not
    inspect JSON (an error message, say) is returned unchanged."""
    try:
        data = json.loads(inspect_text)
    except (TypeError, ValueError):
        return inspect_text
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return inspect_text
    data = data[0]

    state = data.get("State") or {}
    config = data.get("Config") or {}
    policy = (data.get("HostConfig") or {}).get("RestartPolicy") or {}
    health = state.get("Health") or {}

    status = state.get("Status", "unknown")
    if health.get("Status"):
        status += f" ({health['Status']})"
    restart_policy = policy.get("Name") or "no"
    if restart_policy == "on-failure" and policy.get("MaximumRetryCount"):
        restart_policy += f":{policy['MaximumRetryCount']}"
    command = " ".join((config.get("Entrypoint") or []) + (config.get("Cmd") or [])) or "—"

    lines = [
        f"Container   {data.get('Name', '').lstrip('/')}  ({str(data.get('Id', ''))[:12]})",
        f"Image       {config.get('Image', '—')}",
        f"Command     {command}",
        f"Created     {_when(data.get('Created'))}",
    ]
    lines += _section("STATE", [
        f"Status        {status}",
        f"Exit code     {state.get('ExitCode', '—')}",
        f"OOM killed    {_yes_no(state.get('OOMKilled'))}",
        f"Restarts      {data.get('RestartCount', 0)}   (policy: {restart_policy})",
        f"Started       {_when(state.get('StartedAt'))}",
        f"Finished      {_when(state.get('FinishedAt'))}",
    ] + ([f"Error         {state['Error']}"] if state.get("Error") else []))

    if health:
        checks = health.get("Log") or []
        health_lines = [f"Status           {health.get('Status', '—')}",
                        f"Failing streak   {health.get('FailingStreak', 0)}"]
        if checks:
            last = checks[-1]
            health_lines.append(f"Last check       exit {last.get('ExitCode', '—')} at {_when(last.get('End'))}")
            output = str(last.get("Output", "")).strip()
            if output:
                health_lines.append(f"Output           {output.splitlines()[0][:200]}")
        lines += _section("HEALTH", health_lines)

    lines += _section("PORTS", _ports(data))
    lines += _section("NETWORKS", _networks(data))
    lines += _section("MOUNTS", _mounts(data))
    lines += _section("ENVIRONMENT  (secret-looking values hidden — use Inspect for the raw output)",
                      _environment(config))
    return "\n".join(lines)
