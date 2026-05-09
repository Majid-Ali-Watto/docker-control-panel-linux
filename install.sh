#!/bin/bash
# Docker Control Panel - Installation Script

# ── colours ────────────────────────────────────────────────────────────────
BOLD="\033[1m"
DIM="\033[2m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
BLUE="\033[34m"
RESET="\033[0m"

ok()   { echo -e "  ${GREEN}✔${RESET}  $*"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
err()  { echo -e "  ${RED}✘${RESET}  $*"; }
info() { echo -e "  ${CYAN}→${RESET}  $*"; }
step() { echo -e "\n${BOLD}${BLUE}$*${RESET}"; }

# ── banner ──────────────────────────────────────────────────────────────────
echo
echo -e "${BOLD}${CYAN}"
echo "  ██████╗  ██████╗  ██████╗██╗  ██╗███████╗██████╗ "
echo "  ██╔══██╗██╔═══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗"
echo "  ██║  ██║██║   ██║██║     █████╔╝ █████╗  ██████╔╝"
echo "  ██║  ██║██║   ██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗"
echo "  ██████╔╝╚██████╔╝╚██████╗██║  ██╗███████╗██║  ██║"
echo "  ╚═════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝"
echo -e "${RESET}"
echo -e "  ${BOLD}🐳  Docker Control Panel  —  Installer${RESET}"
echo -e "  ${DIM}A graphical Docker manager for Linux${RESET}"
echo
echo -e "  ${DIM}────────────────────────────────────────────────────${RESET}"
echo

# ── script location ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ══════════════════════════════════════════════════════════════════════════════
step "  [1/5]  Checking requirements"
# ══════════════════════════════════════════════════════════════════════════════

# Python 3
if ! command -v python3 &> /dev/null; then
    err "Python 3 is not installed."
    info "Install with:  sudo apt install python3 python3-tk"
    exit 1
fi
PYTHON_VER=$(python3 --version 2>&1)
ok "Python 3 found  ${DIM}(${PYTHON_VER})${RESET}"

# Tkinter
if ! python3 -c "import tkinter" &> /dev/null; then
    err "Tkinter is missing — it is required for the GUI."
    info "Install with:  sudo apt install python3-tk"
    exit 1
fi
ok "Tkinter found"

# Docker
if ! command -v docker &> /dev/null; then
    warn "Docker is not installed — the app will not function without it."
    info "Install with:  sudo apt install docker.io"
    info "Then run:      sudo systemctl enable --now docker"
    echo
    echo -ne "  Continue installation anyway? [y/N] "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo
        err "Installation cancelled."
        exit 1
    fi
else
    DOCKER_VER=$(docker --version 2>&1 | sed 's/Docker version //')
    ok "Docker found  ${DIM}(${DOCKER_VER})${RESET}"
fi

# Terminal emulator
TERMINAL_FOUND=""
for term in tilix gnome-terminal x-terminal-emulator xfce4-terminal \
            konsole mate-terminal terminator xterm; do
    if command -v "$term" &> /dev/null; then
        TERMINAL_FOUND="$term"
        break
    fi
done

if [ -z "$TERMINAL_FOUND" ]; then
    warn "No terminal emulator found — the Container Terminal feature will not work."
    info "Install one with:  sudo apt install tilix"
    echo
    echo -ne "  Continue without terminal support? [y/N] "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo
        err "Installation cancelled."
        exit 1
    fi
else
    ok "Terminal emulator found  ${DIM}(${TERMINAL_FOUND})${RESET}"
fi

# ══════════════════════════════════════════════════════════════════════════════
step "  [2/5]  Verifying project structure"
# ══════════════════════════════════════════════════════════════════════════════

if [ ! -d "$SCRIPT_DIR/src" ]; then
    err "src/ directory not found. The project may be incomplete."
    exit 1
fi

MISSING=0
for dir in src/config src/docker src/ui src/help src/utils; do
    if [ ! -d "$SCRIPT_DIR/$dir" ]; then
        err "Missing directory: $dir"
        MISSING=1
    fi
done
if [ "$MISSING" -eq 1 ]; then
    err "Project structure is incomplete. Please re-download the project."
    exit 1
fi
ok "Project structure verified"

# ══════════════════════════════════════════════════════════════════════════════
step "  [3/5]  Setting permissions"
# ══════════════════════════════════════════════════════════════════════════════

chmod +x "$SCRIPT_DIR/docker-gui"
ok "docker-gui marked executable"

# ══════════════════════════════════════════════════════════════════════════════
step "  [4/5]  Creating desktop entry"
# ══════════════════════════════════════════════════════════════════════════════

# Install the bundled Docker whale icon
ICON_SRC="$SCRIPT_DIR/assets/docker-icon.svg"
ICON_DEST="$HOME/.local/share/icons/docker-control-panel.svg"
mkdir -p "$HOME/.local/share/icons"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$ICON_DEST"
    ok "App icon installed  ${DIM}(${ICON_DEST})${RESET}"
else
    warn "Bundled icon not found — desktop entry will use fallback icon"
    ICON_DEST="utilities-system-monitor"
fi

mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/docker-gui.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Docker Control Panel
Comment=GUI for Docker container management
Exec=$SCRIPT_DIR/docker-gui
Icon=$ICON_DEST
Terminal=false
Categories=System;Utility;
Keywords=docker;container;management;
EOF

chmod +x ~/.local/share/applications/docker-gui.desktop
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons" 2>/dev/null || true
ok "Desktop entry created  ${DIM}(Applications → Docker Control Panel)${RESET}"

# ══════════════════════════════════════════════════════════════════════════════
step "  [5/5]  Creating command-line shortcut"
# ══════════════════════════════════════════════════════════════════════════════

mkdir -p ~/.local/bin
ln -sf "$SCRIPT_DIR/docker-gui" ~/.local/bin/docker-gui 2>/dev/null || true
ok "Symlink created  ${DIM}(~/.local/bin/docker-gui)${RESET}"

# ── done ─────────────────────────────────────────────────────────────────────
echo
echo -e "  ${DIM}────────────────────────────────────────────────────${RESET}"
echo
echo -e "  ${GREEN}${BOLD}🐳  Installation complete!${RESET}"
echo
echo -e "  ${BOLD}Run the app:${RESET}"
echo -e "    ${CYAN}1.${RESET}  Applications menu  →  Docker Control Panel"
echo -e "    ${CYAN}2.${RESET}  Terminal            →  ${BOLD}docker-gui${RESET}"
echo -e "    ${CYAN}3.${RESET}  Direct              →  ${DIM}${SCRIPT_DIR}/docker-gui${RESET}"
echo
echo -e "  ${DIM}Tip: add ~/.local/bin to PATH if 'docker-gui' is not found in your shell.${RESET}"
echo
