#!/bin/bash
# Docker Control Panel - Uninstaller

set -e

# ── colours ────────────────────────────────────────────────────────────────
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
BLUE="\033[34m"
RESET="\033[0m"

ok()   { echo -e "  ${GREEN}✔${RESET}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
step() { echo -e "\n${BOLD}${BLUE}$*${RESET}"; }

echo
echo -e "${BOLD}Docker Control Panel - Uninstaller${RESET}"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

step "[1/5] Removing desktop entry"

if [ -f "$HOME/.local/share/applications/docker-gui.desktop" ]; then
    rm -f "$HOME/.local/share/applications/docker-gui.desktop"
    ok "Desktop entry removed"
else
    warn "Desktop entry not found"
fi

step "[2/5] Removing launcher"

if [ -L "$HOME/.local/bin/docker-gui" ] || [ -f "$HOME/.local/bin/docker-gui" ]; then
    rm -f "$HOME/.local/bin/docker-gui"
    ok "Command-line launcher removed"
else
    warn "Launcher not found"
fi

step "[3/5] Removing icon"

removed_icon=0
for icon in "$HOME/.local/share/icons/hicolor/scalable/apps/docker-control-panel.svg" \
            "$HOME/.local/share/icons/hicolor/256x256/apps/docker-control-panel.png" \
            "$HOME/.local/share/icons/docker-control-panel.svg"; do   # the last one: older versions
    if [ -f "$icon" ]; then
        rm -f "$icon"
        removed_icon=1
    fi
done
if [ "$removed_icon" -eq 1 ]; then
    ok "Application icon removed"
else
    warn "Icon not found"
fi

step "[4/5] Removing Python environment"

if [ -d "$SCRIPT_DIR/.venv" ]; then
    rm -rf "$SCRIPT_DIR/.venv"
    ok "Virtual environment removed"
else
    warn "Virtual environment not found"
fi

step "[5/5] Refreshing desktop database"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

ok "Desktop cache refreshed"

echo
echo -e "${GREEN}${BOLD}Uninstallation complete!${RESET}"
echo
echo "The following were removed:"
echo "  • Applications menu entry"
echo "  • ~/.local/bin/docker-gui"
echo "  • the icon (~/.local/share/icons/hicolor/.../docker-control-panel.*)"
echo "  • .venv (Python dependencies)"
echo
echo "Your project folder was NOT deleted:"
echo "  $SCRIPT_DIR"
echo
echo "If you also want to remove the project, delete it manually:"
echo
echo "  rm -rf \"$SCRIPT_DIR\""