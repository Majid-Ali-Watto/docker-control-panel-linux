"""
Shared helper functions used across multiple dialog modules.
"""

import shlex

_ERROR_HINTS = (
    "error", "failed", "conflict", "permission denied",
    "empty compose file", "not found", "no such",
)


def _quote(value):
    return shlex.quote(str(value))


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


def is_error_output(text):
    """True when docker/sudo output looks like a failure."""
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
