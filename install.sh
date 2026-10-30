#!/bin/sh
# Docker Control Panel - Installation Script (Linux)
#
# One command, no questions: installs the system packages it needs (python3 + tkinter + venv,
# Docker, a terminal emulator), builds a private .venv with the Python dependencies, and adds
# the desktop entry + `docker-gui` command. Safe to run again.
#
# Distros: Debian / Ubuntu and derivatives (apt), Fedora / RHEL / Rocky / Alma / CentOS / Amazon
# Linux (dnf, yum), Arch / Manjaro (pacman), openSUSE / SLE (zypper), Alpine (apk), Void (xbps).
# Init systems for the Docker service: systemd, OpenRC, runit, SysV.

# The first lines must stay POSIX sh: minimal systems (Alpine) have no bash until we install it.
if [ -z "${BASH_VERSION:-}" ]; then
    if ! command -v bash > /dev/null 2>&1; then
        echo "  ->  bash is required - installing it"
        if [ "$(id -u)" -eq 0 ]; then _root=""
        elif command -v sudo > /dev/null 2>&1; then _root="sudo"
        elif command -v doas > /dev/null 2>&1; then _root="doas"
        else echo "  x  Install bash first (needs root: no sudo or doas found)."; exit 1; fi
        if   command -v apk > /dev/null 2>&1;         then $_root apk add --no-cache bash
        elif command -v apt-get > /dev/null 2>&1;     then $_root apt-get install -y bash
        elif command -v dnf > /dev/null 2>&1;         then $_root dnf install -y bash
        elif command -v yum > /dev/null 2>&1;         then $_root yum install -y bash
        elif command -v pacman > /dev/null 2>&1;      then $_root pacman -S --needed --noconfirm bash
        elif command -v zypper > /dev/null 2>&1;      then $_root zypper --non-interactive install bash
        elif command -v xbps-install > /dev/null 2>&1; then $_root xbps-install -Sy bash   # -S: a fresh image has no package index
        fi
        command -v bash > /dev/null 2>&1 || { echo "  x  Could not install bash."; exit 1; }
    fi
    exec bash "$0" "$@"
fi

set -u

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
die()  { err "$*"; exit 1; }

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

# Directory of this script, following symlinks
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    case "$SOURCE" in /*) ;; *) SOURCE="$DIR/$SOURCE" ;; esac
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
MIN_PY_MINOR=8

[ "$(uname -s)" = "Linux" ] || die "This installer is for Linux (found $(uname -s))."

# ── helpers ─────────────────────────────────────────────────────────────────
ROOT_CMD=""
if [ "$(id -u)" -ne 0 ]; then
    if   command -v sudo > /dev/null 2>&1; then ROOT_CMD="sudo"
    elif command -v doas > /dev/null 2>&1; then ROOT_CMD="doas"
    else ROOT_CMD="__missing__"; fi
else
    [ -z "${SUDO_USER:-}" ] && warn "Running as root: the desktop entry and command go to root's home, not a regular user's."
fi

# Run a command as root (sudo asks for the password itself, once, thanks to its timestamp cache).
as_root() {
    if [ "$ROOT_CMD" = "__missing__" ]; then
        err "Need root to install packages but neither sudo nor doas is available. Run this script as root."
        return 1
    fi
    $ROOT_CMD "$@"
}

# Keep in sync with src/utils/terminals.py
has_term() {
    for t in tilix gnome-terminal ptyxis kgx x-terminal-emulator xfce4-terminal konsole mate-terminal \
             lxterminal qterminal terminator kitty alacritty wezterm foot urxvt xterm; do
        command -v "$t" &> /dev/null && return 0
    done
    return 1
}

# A Python this app can run on: 3.$MIN_PY_MINOR+, with venv and a Tk of at least 8.6
python_usable() {
    "$1" -c "import sys, tkinter, venv, ensurepip; sys.exit(sys.version_info < (3, $MIN_PY_MINOR) or tkinter.TkVersion < 8.6)" &> /dev/null
}

pick_python() {
    local candidate
    for candidate in python3 python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3.8; do
        command -v "$candidate" &> /dev/null || continue
        if python_usable "$candidate"; then command -v "$candidate"; return 0; fi
    done
    return 1
}

PYTHON=""
DOCKER_NEW=0
REQUIRED=()     # without these the app cannot start
OPTIONAL=()     # nice to have; failure only warns

# ══════════════════════════════════════════════════════════════════════════════
step "  [1/6]  Detecting your system"
# ══════════════════════════════════════════════════════════════════════════════

# shellcheck disable=SC1091
[ -r /etc/os-release ] && . /etc/os-release
DISTRO="${PRETTY_NAME:-Linux}"
FAMILY=" ${ID:-} ${ID_LIKE:-} "

if   command -v apt-get     &> /dev/null; then PM=apt
elif command -v dnf         &> /dev/null; then PM=dnf
elif command -v yum         &> /dev/null; then PM=yum
elif command -v pacman      &> /dev/null; then PM=pacman
elif command -v zypper      &> /dev/null; then PM=zypper
elif command -v apk         &> /dev/null; then PM=apk
elif command -v xbps-install &> /dev/null; then PM=xbps
else PM=""
fi
ok "${DISTRO}  ${DIM}(package manager: ${PM:-none found}, $(uname -m))${RESET}"

if [ "${ID:-}" = "nixos" ]; then
    err "NixOS has no FHS paths for this installer to work with. Run the app from a shell instead:"
    info "nix-shell -p 'python3.withPackages (p: [ p.tkinter p.pillow p.ttkbootstrap ])' docker --run ./docker_gui_modular.py"
    exit 1
fi
if [ -e /run/ostree-booted ]; then
    warn "Immutable system (ostree): packages cannot be installed in place. If tkinter or Docker are missing,"
    info "layer them (rpm-ostree install python3-tkinter docker) or run this inside a toolbox / distrobox."
fi

# Package names differ per distro family.
PKG_PY_VERSIONED=""     # fallback sets for a system Python that is too old: "version|packages"
case "$PM" in
    apt)    PKG_PY="python3 python3-venv python3-pip"; PKG_TK="python3-tk"
            PKG_DOCKER="docker.io"; PKG_SECRET="libsecret-tools"
            PKG_PY_VERSIONED="3.12|python3.12 python3.12-venv python3.12-tk
3.11|python3.11 python3.11-venv python3.11-tk
3.10|python3.10 python3.10-venv python3.10-tk
3.9|python3.9 python3.9-venv python3.9-tk" ;;
    dnf|yum) PKG_PY="python3 python3-pip";             PKG_TK="python3-tkinter"
            PKG_SECRET="libsecret"
            # Fedora ships Moby; Amazon Linux has `docker`; RHEL / Rocky / Alma / CentOS need Docker's own repo
            case "$FAMILY" in
                *" fedora "*) PKG_DOCKER="moby-engine" ;;
                *)            PKG_DOCKER="docker" ;;
            esac
            PKG_PY_VERSIONED="3.12|python3.12 python3.12-tkinter python3.12-pip
3.11|python3.11 python3.11-tkinter python3.11-pip
3.9|python3.9 python3.9-tkinter python3.9-pip" ;;
    pacman) PKG_PY="python python-pip";                PKG_TK="tk"
            PKG_DOCKER="docker"; PKG_SECRET="libsecret" ;;
    zypper) PKG_PY="python3 python3-pip";              PKG_TK="python3-tk"
            PKG_DOCKER="docker"; PKG_SECRET="libsecret-tools"
            PKG_PY_VERSIONED="3.12|python312 python312-tk python312-pip
3.11|python311 python311-tk python311-pip
3.10|python310 python310-tk python310-pip" ;;
    apk)    PKG_PY="python3 py3-pip";                  PKG_TK="python3-tkinter"
            PKG_DOCKER="docker"; PKG_SECRET="libsecret" ;;
    xbps)   PKG_PY="python3 python3-pip";              PKG_TK="python3-tkinter"
            PKG_DOCKER="docker"; PKG_SECRET="libsecret" ;;
esac
PKG_TERM="xterm"

pm_install() {
    case "$PM" in
        apt)     as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@" ;;
        dnf)     as_root dnf install -y "$@" ;;
        yum)     as_root yum install -y "$@" ;;
        # "target not found" usually means a never-synced package database: sync it and retry once
        pacman)  as_root pacman -S --needed --noconfirm "$@" || as_root pacman -Sy --needed --noconfirm "$@" ;;
        zypper)  as_root zypper --non-interactive install "$@" ;;
        apk)     as_root apk add --no-cache "$@" ;;
        xbps)    as_root xbps-install -y "$@" || as_root xbps-install -Sy "$@" ;;
        *)       return 1 ;;
    esac
}

# RHEL / Rocky / Alma / CentOS / Oracle have no Docker in their own repos: use Docker's official one
install_docker_from_docker_repo() {
    local repo="centos" file="/etc/yum.repos.d/docker-ce.repo"
    [[ "$FAMILY" == *" fedora "* ]] && repo="fedora"
    info "Adding Docker's package repository"
    as_root "$PM" install -y dnf-plugins-core > /dev/null 2>&1 || as_root "$PM" install -y yum-utils > /dev/null 2>&1
    as_root "$PM" config-manager --add-repo "https://download.docker.com/linux/$repo/docker-ce.repo" > /dev/null 2>&1 \
        || as_root "$PM" config-manager addrepo --from-repofile="https://download.docker.com/linux/$repo/docker-ce.repo" > /dev/null 2>&1 \
        || return 1
    if ! as_root "$PM" install -y docker-ce docker-ce-cli containerd.io > /dev/null 2>&1; then
        as_root rm -f "$file"        # an unreachable repo would make every later dnf / yum command fail
        return 1
    fi
}

enable_docker_service() {
    if [ -d /run/systemd/system ]; then
        as_root systemctl enable --now docker
    elif command -v rc-update &> /dev/null; then
        as_root rc-update add docker default && as_root rc-service docker start
    elif [ -d /etc/sv/docker ] && [ -d /var/service ]; then
        as_root ln -sf /etc/sv/docker /var/service/
    elif command -v service &> /dev/null; then
        as_root service docker start
    else
        return 1
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
step "  [2/6]  Installing system packages"
# ══════════════════════════════════════════════════════════════════════════════

command -v python3 &> /dev/null || REQUIRED+=($PKG_PY)
if command -v python3 &> /dev/null; then
    python3 -c "import tkinter" &> /dev/null || REQUIRED+=($PKG_TK)
    python3 -c "import venv, ensurepip" &> /dev/null || REQUIRED+=($PKG_PY)
else
    REQUIRED+=($PKG_TK)
fi
command -v docker &> /dev/null || { OPTIONAL+=($PKG_DOCKER); DOCKER_NEW=1; }
has_term || OPTIONAL+=($PKG_TERM)
command -v secret-tool &> /dev/null || OPTIONAL+=($PKG_SECRET)
command -v sudo &> /dev/null || [ "$(id -u)" -eq 0 ] || OPTIONAL+=(sudo)   # the app runs docker through sudo

if [ -z "$PM" ] && { [ "${#REQUIRED[@]}" -gt 0 ] || [ "${#OPTIONAL[@]}" -gt 0 ]; }; then
    warn "No supported package manager (apt, dnf, yum, pacman, zypper, apk, xbps) — install these yourself:"
    info "python 3.$MIN_PY_MINOR+ with venv + tkinter, docker, a terminal emulator"
elif [ "${#REQUIRED[@]}" -gt 0 ]; then
    [ "$PM" = apt ] && info "Refreshing package lists" && as_root apt-get update -qq
    info "Installing: ${REQUIRED[*]}"
    pm_install "${REQUIRED[@]}" > /dev/null || die "Could not install: ${REQUIRED[*]}"
elif [ "${#OPTIONAL[@]}" -gt 0 ]; then
    [ "$PM" = apt ] && info "Refreshing package lists" && as_root apt-get update -qq
else
    ok "Everything already installed"
fi

command -v python3 &> /dev/null || die "Python 3 is not installed."
if ! PYTHON="$(pick_python)"; then
    # The distro's default Python is older than we need (CentOS / RHEL 8, openSUSE Leap 15, ...): try newer ones side by side
    while IFS='|' read -r version packages; do
        [ -n "$version" ] || continue
        info "System Python is too old — trying Python $version"
        # shellcheck disable=SC2086
        pm_install $packages > /dev/null 2>&1 < /dev/null || continue
        PYTHON="$(pick_python)" && break
    done <<< "$PKG_PY_VERSIONED"
fi
if [ -z "$PYTHON" ]; then
    python3 -c "import tkinter" &> /dev/null || die "Tkinter is missing and could not be installed — install your distro's python3 tkinter package."
    python3 -c "import venv, ensurepip" &> /dev/null || die "The Python venv module is missing — install your distro's python3-venv package."
    die "Python 3.$MIN_PY_MINOR or newer with Tk 8.6 is required (found $(python3 --version 2>&1))."
fi
ok "Python  ${DIM}($("$PYTHON" --version 2>&1), tkinter $("$PYTHON" -c 'import tkinter; print(tkinter.TkVersion)'), venv)${RESET}"

# Extras last: a problem with one of them (an unreachable Docker repository ...) must never get in the
# way of the Python the app needs
if [ -n "$PM" ]; then
    # one by one, so a package missing from this distro's repos does not block the others
    for pkg in ${OPTIONAL[@]+"${OPTIONAL[@]}"}; do
        info "Installing: $pkg"
        if ! pm_install "$pkg" > /dev/null 2>&1 < /dev/null; then
            if [ "$pkg" = "$PKG_DOCKER" ] && { [ "$PM" = dnf ] || [ "$PM" = yum ]; } && install_docker_from_docker_repo; then
                continue
            fi
            warn "Could not install '$pkg' — continuing without it."
            [ "$pkg" = "$PKG_DOCKER" ] && DOCKER_NEW=0
        fi
    done
fi


if command -v docker &> /dev/null; then
    ok "Docker  ${DIM}($(docker --version 2>&1 | sed 's/Docker version //'))${RESET}"
    if [ "$DOCKER_NEW" -eq 1 ]; then
        enable_docker_service &> /dev/null && ok "Docker service enabled and started" \
            || warn "Could not start the Docker service — use the Start button in the app."
    fi
else
    warn "Docker is not installed — the app will not manage anything until it is. See https://docs.docker.com/engine/install/"
fi
has_term && ok "Terminal emulator found" || warn "No terminal emulator — the Container Terminal feature will not work."

# ══════════════════════════════════════════════════════════════════════════════
step "  [3/6]  Setting up the Python environment"
# ══════════════════════════════════════════════════════════════════════════════

[ -d "$SCRIPT_DIR/src" ] && [ -f "$SCRIPT_DIR/docker_gui_modular.py" ] \
    || die "src/ or docker_gui_modular.py not found. The project may be incomplete — re-download it."

deps_ok() { "$VENV/bin/python" -c "import tkinter, ttkbootstrap, PIL" &> /dev/null; }

# A .venv copied from another machine (or left over from an old system Python) is broken: rebuild it.
if [ -d "$VENV" ] && ! deps_ok; then
    info "Existing .venv is unusable here — rebuilding it"
    rm -rf "$VENV"
fi
if [ ! -d "$VENV" ]; then
    "$PYTHON" -m venv "$VENV" || die "Could not create the virtual environment at $VENV"
fi
# old distros ship a pip that cannot read newer wheel tags
"$VENV/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade pip &> /dev/null || true
"$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$SCRIPT_DIR/requirements.txt" \
    || die "pip could not install the requirements (network down, or no prebuilt Pillow for $(uname -m)?). Re-run ./install.sh when online."
deps_ok || die "The Python dependencies installed but cannot be imported."
ok "Dependencies installed  ${DIM}(${VENV})${RESET}"

# ══════════════════════════════════════════════════════════════════════════════
step "  [4/6]  Setting permissions"
# ══════════════════════════════════════════════════════════════════════════════

chmod +x "$SCRIPT_DIR/docker-gui"
ok "docker-gui marked executable"

# ══════════════════════════════════════════════════════════════════════════════
step "  [5/6]  Creating desktop entry"
# ══════════════════════════════════════════════════════════════════════════════

# Install the app icon into the user's hicolor icon theme (the standard place menus look in:
# GNOME, KDE, XFCE, Cinnamon, MATE ...): the SVG for any size, plus a 256 px PNG for launchers
# that cannot draw SVG. The menu entry then refers to it by name.
ICON_NAME="docker-control-panel"
ICON_ROOT="$HOME/.local/share/icons/hicolor"
if [ -f "$SCRIPT_DIR/assets/docker-icon.svg" ]; then
    mkdir -p "$ICON_ROOT/scalable/apps" "$ICON_ROOT/256x256/apps"
    cp "$SCRIPT_DIR/assets/docker-icon.svg" "$ICON_ROOT/scalable/apps/$ICON_NAME.svg"
    [ -f "$SCRIPT_DIR/assets/docker-icon.png" ] && cp "$SCRIPT_DIR/assets/docker-icon.png" "$ICON_ROOT/256x256/apps/$ICON_NAME.png"
    rm -f "$HOME/.local/share/icons/$ICON_NAME.svg"      # older versions kept it here
    gtk-update-icon-cache -f -t "$ICON_ROOT" 2>/dev/null || true
    ICON_DEST="$ICON_NAME"
    ok "App icon installed  ${DIM}(${ICON_ROOT}/scalable/apps/${ICON_NAME}.svg)${RESET}"
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
Exec="$SCRIPT_DIR/docker-gui"
Icon=$ICON_DEST
Terminal=false
Categories=System;Utility;
Keywords=docker;container;management;
EOF

chmod +x ~/.local/share/applications/docker-gui.desktop
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
ok "Desktop entry created  ${DIM}(Applications → Docker Control Panel)${RESET}"

# ══════════════════════════════════════════════════════════════════════════════
step "  [6/6]  Creating command-line shortcut"
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
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo -e "  ${DIM}Tip: add ~/.local/bin to PATH (log out and in again) to use 'docker-gui' in a shell.${RESET}"; echo ;;
esac
echo -e "  ${BOLD}Privacy & Terms${RESET}"
echo -e "  ${DIM}Docker Control Panel has no telemetry and keeps its data on your computer. Please read${RESET}"
echo -e "  ${DIM}${SCRIPT_DIR}/PRIVACY.md and TERMS.md; the app shows both on first start${RESET}"
echo -e "  ${DIM}(and from its Docker home page) and asks you to accept before it runs.${RESET}"
echo
