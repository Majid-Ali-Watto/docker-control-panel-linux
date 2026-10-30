#!/bin/sh
# Runs INSIDE a distro container (as root): installs the app from a copy of /src and checks the result.
# Used by tests/distro_smoke.sh and CI. Prints one final line: "RESULT: PASS" or "RESULT: FAIL <why>".
fail() { echo "RESULT: FAIL $*"; exit 1; }

# a copy, so the mounted checkout stays clean
mkdir -p /app && cp -r /src/. /app/ && cd /app && rm -rf .venv .git

./install.sh > /tmp/install1.log 2>&1; rc=$?
[ "$rc" -eq 0 ] || { sed 's/\x1b\[[0-9;]*m//g' /tmp/install1.log | tail -25; fail "install.sh (first run) exited $rc"; }
./install.sh > /tmp/install2.log 2>&1; rc=$?
[ "$rc" -eq 0 ] || { sed 's/\x1b\[[0-9;]*m//g' /tmp/install2.log | tail -25; fail "install.sh (second run) exited $rc"; }
sed 's/\x1b\[[0-9;]*m//g' /tmp/install1.log | grep -E "✔|✘|⚠" | head -12

.venv/bin/python - <<'PY' || fail "imports in .venv"
import sys, tkinter, ttkbootstrap, PIL
from src.utils import platform_utils as plat, utils
print("python", sys.version.split()[0], "| tk", tkinter.TkVersion, "| ttkbootstrap", ttkbootstrap.__version__ if hasattr(ttkbootstrap, "__version__") else "ok",
      "| init:", plat.service_manager(), "| pm:", plat.package_manager())
PY

# the launcher must find the project through the symlink and get as far as Tk (there is no display here)
out=$(~/.local/bin/docker-gui 2>&1 | tail -3)
case "$out" in
    *"not installed yet"*) fail "launcher does not find the install: $out" ;;
    *"no display"*|*"couldn't connect to display"*|*TclError*) ;;
    *) echo "launcher output: $out" ;;
esac

# the menu entry must use the shipped icon, installed under the standard icon theme
icons=~/.local/share/icons/hicolor
# (cksum, not cmp: minimal images such as Arch or openSUSE have no diffutils)
same() { [ -f "$2" ] && [ "$(cksum < "$1")" = "$(cksum < "$2")" ]; }
same assets/docker-icon.svg "$icons/scalable/apps/docker-control-panel.svg" || fail "installed SVG icon differs from assets/docker-icon.svg"
same assets/docker-icon.png "$icons/256x256/apps/docker-control-panel.png" || fail "installed PNG icon differs from assets/docker-icon.png"
grep -q '^Icon=docker-control-panel$' ~/.local/share/applications/docker-gui.desktop || fail "desktop entry does not use the installed icon"
echo "icon: installed and used by the menu entry"

.venv/bin/python -m unittest tests.test_linux_compat > /tmp/unit.log 2>&1 || { tail -15 /tmp/unit.log; fail "unit tests"; }
tail -3 /tmp/unit.log | head -2
command -v docker > /dev/null 2>&1 && docker --version
echo "RESULT: PASS"
