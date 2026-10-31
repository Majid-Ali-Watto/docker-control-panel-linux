"""
Shared helper functions used across multiple dialog modules.
"""

import json
import os
import shlex

_ERROR_HINTS = (
    "error", "failed", "conflict", "permission denied",
    "empty compose file", "not found", "no such",
)


def _quote(value):
    return shlex.quote(str(value))


def _split_lines(raw_text):
    """One value per non-blank line — for KEY=VALUE entries, whose values may contain commas."""
    return [line.strip() for line in str(raw_text).splitlines() if line.strip()]


def _split_csv_lines(raw_text):
    values = []
    for line in str(raw_text).splitlines():
        for part in line.split(','):
            part = part.strip()
            if part:
                values.append(part)
    return values


def _join_flag_values(flag, values):
    return ''.join(f" {flag} {_quote(value)}" for value in values if str(value).strip())


def _join_quoted(values):
    return ' '.join(_quote(value) for value in values if str(value).strip())


def _compose_files_to_args(config_files):
    files = _split_csv_lines(config_files)
    return ' '.join(f"-f {_quote(path)}" for path in files)


def _center_dialog(dialog, min_width=420):
    dialog.update_idletasks()
    width = max(dialog.winfo_reqwidth() + 20, min_width)
    height = dialog.winfo_reqheight() + 16
    x = (dialog.winfo_screenwidth() - width) // 2
    y = (dialog.winfo_screenheight() - height) // 2
    dialog.geometry(f"{width}x{height}+{x}+{y}")


def owned_by_user(command, path):
    """`command`, which writes `path` on the host, followed by handing the file back to the user
    when it runs through sudo (it would stay root-owned in the user's folder otherwise)."""
    from src.config.config_manager import get_sudo_password
    if not get_sudo_password() or os.geteuid() == 0:
        return command
    return f"{command} && chown -R {os.getuid()}:{os.getgid()} {_quote(path)}"


def parse_json_records(text):
    """Objects from docker's `--format json` output: one JSON array (compose ls, older compose ps)
    or one object per line (newer compose ps). Lines that are not JSON (WARN …) are skipped."""
    text = str(text or "").strip()
    try:
        data = json.loads(text or "[]")
        return [item for item in (data if isinstance(data, list) else [data]) if isinstance(item, dict)]
    except ValueError:
        pass
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith(("{", "[")):
            continue
        try:
            data = json.loads(line)
        except ValueError:
            continue
        records.extend(item for item in (data if isinstance(data, list) else [data]) if isinstance(item, dict))
    return records


def is_error_output(text):
    """True when a command failed: its exit status when run_cmd supplied one (output text alone
    misleads — `docker stop error-page` prints the name), else the output looks like a failure."""
    returncode = getattr(text, "returncode", None)
    if returncode is not None:
        return returncode != 0
    text = str(text).lower()
    return any(hint in text for hint in _ERROR_HINTS)


def _make_output_callback(show_text_output_callback, title="", refresh_callback=None, root=None):
    def callback(result):
        text = f"{title}\n\n{result}".strip() if title else result
        show_text_output_callback(text)
        if refresh_callback and root:
            if not is_error_output(result):
                root.after(800, refresh_callback)
    return callback
