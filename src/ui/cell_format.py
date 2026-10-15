"""
Human-readable table cells.

Docker prints machine-friendly text (ISO timestamps with a zone name, '388MB', one port mapping
per address family). `format_cell` turns a cell into what the table shows; it is display-only,
because sorting, the date filter and the row actions work on the original text.
"""

import os
import re
from datetime import datetime

# '2026-10-15 15:06:49 +0500 PKT', also with fractional seconds ('...:04.770160954 +0500 PKT')
DOCKER_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})")
DATE_COLUMNS = ("CREATED",)

_SIZE_COLUMNS = {"MEM USAGE", "NET I/O", "BLOCK I/O", "RECLAIMABLE"}
_UNIT = re.compile(r"(\d)(?=(?:[kKMGTP]i?)?B\b)")           # '388MB' -> '388 MB'
_STATE_COUNT = re.compile(r"(\w)\((\d+)\)")                  # 'exited(4)' -> 'exited (4)'
_ANY_ADDRESS = ("0.0.0.0:", "[::]:", ":::")                  # published on every interface


def _date(text):
    m = DOCKER_DATE.search(text)
    return datetime(*map(int, m.groups())).strftime("%d %b %Y, %H:%M") if m else text


def _ports(text):
    """'0.0.0.0:80->80/tcp, [::]:80->80/tcp' -> '80 → 80/tcp' (IPv4 and IPv6 listed once)."""
    shown = []
    for part in (p.strip() for p in text.split(",")):
        for prefix in _ANY_ADDRESS:
            if part.startswith(prefix):
                part = part[len(prefix):]
        part = part.replace("->", " → ")
        if part and part not in shown:
            shown.append(part)
    return ", ".join(shown)


def _files(text):
    """Comma-joined compose files -> one per ', ' with the home directory written as '~'."""
    home = os.path.expanduser("~") + os.sep
    return ", ".join("~/" + f[len(home):] if f.startswith(home) else f
                     for f in (f.strip() for f in text.split(",")))


_EXIT_CODE = re.compile(r"exited \((\d+)\)", re.IGNORECASE)


def status_tone(text):
    """How a container's STATUS reads at a glance: 'bad' (unhealthy, restarting, dead), 'warn'
    (exited with a non-zero code, paused), 'ok' (healthy) or None (nothing to flag)."""
    lowered = str(text).lower()
    if "unhealthy" in lowered or lowered.startswith(("restarting", "dead")):
        return "bad"
    exited = _EXIT_CODE.match(lowered.replace("exited(", "exited ("))
    if (exited and exited.group(1) != "0") or "paused" in lowered:
        return "warn"
    if "(healthy)" in lowered:
        return "ok"
    return None


def format_cell(column, text):
    """The text to show for a cell of `column` (unchanged when there is nothing to improve)."""
    text = str(text)
    if column in DATE_COLUMNS:
        return _date(text)
    if column == "PORTS":
        return _ports(text)
    if column == "CONFIG FILES":
        return _files(text)
    if column == "STATUS":
        return _STATE_COUNT.sub(r"\1 (\2)", text)
    if "SIZE" in column or column in _SIZE_COLUMNS:
        return _UNIT.sub(r"\1 ", text)
    return text
