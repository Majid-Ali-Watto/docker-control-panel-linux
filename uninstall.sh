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

step "[1/4] Removing desktop entry"

if [ -f "$HOME/.local/share/applications/docker-gui.desktop" ]; then
    rm -f "$HOME/.local/share/applications/docker-gui.desktop"
    ok "Desktop entry removed"
else
    warn "Desktop entry not found"
fi

step "[2/4] Removing launcher"

if [ -L "$HOME/.local/bin/docker-gui" ] || [ -f "$HOME/.local/bin/docker-gui" ]; then
    rm -f "$HOME/.local/bin/docker-gui"
    ok "Command-line launcher removed"
else
    warn "Launcher not found"
fi

step "[3/4] Removing icon"

if [ -f "$HOME/.local/share/icons/docker-control-panel.svg" ]; then
    rm -f "$HOME/.local/share/icons/docker-control-panel.svg"
    ok "Application icon removed"
else
    warn "Icon not found"
fi

step "[4/4] Refreshing desktop database"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons" 2>/dev/null || true

ok "Desktop cache refreshed"

echo
echo -e "${GREEN}${BOLD}Uninstallation complete!${RESET}"
echo
echo "The following were removed:"
echo "  • Applications menu entry"
echo "  • ~/.local/bin/docker-gui"
echo "  • ~/.local/share/icons/docker-control-panel.svg"
echo
echo "Your project folder was NOT deleted:"
echo "  $SCRIPT_DIR"
echo
echo "If you also want to remove the project, delete it manually:"
echo
echo "  rm -rf \"$SCRIPT_DIR\""