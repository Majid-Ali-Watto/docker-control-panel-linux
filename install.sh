#!/bin/bash
# Docker Control Panel - Installation Script (Linux and macOS; Windows: install.ps1 / install.bat)
#
# One command, no questions: installs the system packages it needs (python3 + tkinter + venv,
# Docker, a terminal emulator), builds a private .venv with the Python dependencies, and adds
# the desktop entry + `docker-gui` command. Safe to run again.
#
#   Linux  apt / dnf / pacman / zypper, desktop entry, ~/.local/bin/docker-gui
#   macOS  Homebrew (installed if missing), Docker Desktop, ~/Applications/Docker Control Panel.app
#
# Written for bash 3.2 (what macOS ships): no associative arrays, empty arrays guarded for `set -u`.

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
echo -e "  ${DIM}A graphical Docker manager for Linux, macOS and Windows${RESET}"
echo
echo -e "  ${DIM}────────────────────────────────────────────────────${RESET}"
echo

# Directory of this script, following symlinks (BSD readlink has no -f before macOS 12.3)
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    case "$SOURCE" in /*) ;; *) SOURCE="$DIR/$SOURCE" ;; esac
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
MIN_PY_MINOR=10

case "$(uname -s)" in
    Linux)  OS=linux ;;
    Darwin) OS=mac ;;
    *)      die "Unsupported system: $(uname -s). On Windows run install.ps1 (or double-click install.bat)." ;;
esac

if [ "$OS" = linux ] && [ "$(id -u)" -eq 0 ] && [ -z "${SUDO_USER:-}" ]; then
    warn "Running as root: the desktop entry and command go to root's home, not a regular user's."
fi

# ── helpers ─────────────────────────────────────────────────────────────────
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    command -v sudo &> /dev/null && SUDO="sudo" || SUDO="__missing__"
fi

# Run a command as root (sudo asks for the password itself, once, thanks to its timestamp cache).
as_root() {
    if [ "$SUDO" = "__missing__" ]; then
        err "Need root to install packages but sudo is not available. Run this script as root."
        return 1
    fi
    $SUDO "$@"
}

has_term() {
    for t in tilix gnome-terminal x-terminal-emulator xfce4-terminal konsole \
             mate-terminal terminator xterm; do
        command -v "$t" &> /dev/null && return 0
    done
    return 1
}

# A Python this app can run on: 3.10+, with venv and a Tk of at least 8.6 (macOS's own is 8.5)
python_usable() {
    "$1" -c "import sys, tkinter, venv, ensurepip; sys.exit(sys.version_info < (3, $MIN_PY_MINOR) or tkinter.TkVersion < 8.6)" &> /dev/null
}

pick_python() {
    local candidate brew_bin=""
    command -v brew &> /dev/null && brew_bin="$(brew --prefix 2> /dev/null)/bin"
    for candidate in python3 python3.14 python3.13 python3.12 python3.11 python3.10 \
                     ${brew_bin:+"$brew_bin/python3.12"} ${brew_bin:+"$brew_bin/python3"}; do
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

if [ "$OS" = mac ]; then
    ok "macOS $(sw_vers -productVersion 2> /dev/null)  ${DIM}($(uname -m))${RESET}"
else
    # shellcheck disable=SC1091
    [ -r /etc/os-release ] && . /etc/os-release
    DISTRO="${PRETTY_NAME:-$(uname -s)}"
    FAMILY=" ${ID:-} ${ID_LIKE:-} "

    if   command -v apt-get &> /dev/null; then PM=apt
    elif command -v dnf     &> /dev/null; then PM=dnf
    elif command -v pacman  &> /dev/null; then PM=pacman
    elif command -v zypper  &> /dev/null; then PM=zypper
    else PM=""
    fi
    ok "${DISTRO}  ${DIM}(package manager: ${PM:-none found})${RESET}"

    # Package names differ per distro family.
    case "$PM" in
        apt)    PKG_PY="python3 python3-venv python3-pip"; PKG_TK="python3-tk"
                PKG_DOCKER="docker.io"; PKG_SECRET="libsecret-tools" ;;
        dnf)    PKG_PY="python3 python3-pip";              PKG_TK="python3-tkinter"
                PKG_DOCKER="moby-engine"; PKG_SECRET="libsecret"
                [[ "$FAMILY" == *" rhel "* || "$FAMILY" == *" centos "* ]] && PKG_DOCKER="docker" ;;
        pacman) PKG_PY="python python-pip";                PKG_TK="tk"
                PKG_DOCKER="docker"; PKG_SECRET="libsecret" ;;
        zypper) PKG_PY="python3 python3-pip";              PKG_TK="python3-tk"
                PKG_DOCKER="docker"; PKG_SECRET="libsecret-tools" ;;
    esac
    PKG_TERM="xterm"
fi

pm_install() {
    case "$PM" in
        apt)    as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@" ;;
        dnf)    as_root dnf install -y "$@" ;;
        # "target not found" usually means a never-synced package database: sync it and retry once
        pacman) as_root pacman -S --needed --noconfirm "$@" || as_root pacman -Sy --needed --noconfirm "$@" ;;
        zypper) as_root zypper --non-interactive install "$@" ;;
        *)      return 1 ;;
    esac
}

# ══════════════════════════════════════════════════════════════════════════════
step "  [2/6]  Installing system packages"
# ══════════════════════════════════════════════════════════════════════════════

if [ "$OS" = mac ]; then
    # Homebrew is how Python (with a modern Tk) and Docker Desktop get installed
    if ! command -v brew &> /dev/null; then
        for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
            [ -x "$b" ] && eval "$("$b" shellenv)" && break
        done
    fi
    if ! command -v brew &> /dev/null; then
        info "Installing Homebrew (needs your password once)"
        sudo -v || die "Administrator access is needed to install Homebrew."
        NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
            || die "Homebrew could not be installed. See https://brew.sh and run this script again."
        for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
            [ -x "$b" ] && eval "$("$b" shellenv)" && break
        done
        command -v brew &> /dev/null || die "Homebrew was installed but 'brew' is not on PATH."
    fi
    ok "Homebrew  ${DIM}($(brew --prefix))${RESET}"

    PYTHON="$(pick_python)" || {
        info "Installing: python@3.12 python-tk@3.12"
        brew install python@3.12 python-tk@3.12 > /dev/null || die "Could not install Python with Homebrew."
        PYTHON="$(pick_python)" || die "No usable Python (3.$MIN_PY_MINOR+ with Tk 8.6) found after installing."
    }

    if ! command -v docker &> /dev/null && [ ! -d /Applications/Docker.app ]; then
        info "Installing: Docker Desktop"
        if brew install --cask docker-desktop > /dev/null 2>&1 || brew install --cask docker > /dev/null 2>&1; then
            DOCKER_NEW=1
        else
            warn "Could not install Docker Desktop — get it from https://www.docker.com/products/docker-desktop/"
        fi
    fi
else
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

    if [ -z "$PM" ] && { [ "${#REQUIRED[@]}" -gt 0 ] || [ "${#OPTIONAL[@]}" -gt 0 ]; }; then
        warn "No supported package manager (apt, dnf, pacman, zypper) — install these yourself:"
        info "python 3.$MIN_PY_MINOR+ with venv + tkinter, docker, a terminal emulator"
    elif [ "${#REQUIRED[@]}" -gt 0 ] || [ "${#OPTIONAL[@]}" -gt 0 ]; then
        [ "$PM" = apt ] && info "Refreshing package lists" && as_root apt-get update -qq
        if [ "${#REQUIRED[@]}" -gt 0 ]; then
            info "Installing: ${REQUIRED[*]}"
            pm_install "${REQUIRED[@]}" > /dev/null || die "Could not install: ${REQUIRED[*]}"
        fi
        # one by one, so a package missing from this distro's repos does not block the others
        for pkg in ${OPTIONAL[@]+"${OPTIONAL[@]}"}; do
            info "Installing: $pkg"
            pm_install "$pkg" > /dev/null || { warn "Could not install '$pkg' — continuing without it."; [ "$pkg" = "$PKG_DOCKER" ] && DOCKER_NEW=0; }
        done
    else
        ok "Everything already installed"
    fi

    command -v python3 &> /dev/null || die "Python 3 is not installed."
    PYTHON="$(pick_python)" || {
        python3 -c "import tkinter" &> /dev/null || die "Tkinter is missing and could not be installed — install your distro's python3 tkinter package."
        python3 -c "import venv, ensurepip" &> /dev/null || die "The Python venv module is missing — install your distro's python3-venv package."
        die "Python 3.$MIN_PY_MINOR or newer is required (found $(python3 --version 2>&1))."
    }
fi
ok "Python  ${DIM}($("$PYTHON" --version 2>&1), tkinter $("$PYTHON" -c 'import tkinter; print(tkinter.TkVersion)'), venv)${RESET}"

if command -v docker &> /dev/null || [ -d /Applications/Docker.app ]; then
    if command -v docker &> /dev/null; then
        ok "Docker  ${DIM}($(docker --version 2>&1 | sed 's/Docker version //'))${RESET}"
    else
        ok "Docker Desktop installed  ${DIM}(open it once to finish its setup)${RESET}"
    fi
    if [ "$DOCKER_NEW" -eq 1 ]; then
        if [ "$OS" = mac ]; then
            open -a Docker &> /dev/null && ok "Docker Desktop is starting — accept its first-run prompts" \
                || warn "Open Docker Desktop once to finish its setup."
        elif command -v systemctl &> /dev/null; then
            as_root systemctl enable --now docker &> /dev/null && ok "Docker service enabled and started" \
                || warn "Could not start the Docker service — use the Start button in the app."
        fi
    fi
else
    warn "Docker is not installed — the app will not manage anything until it is."
fi
if [ "$OS" = linux ]; then
    has_term && ok "Terminal emulator found" || warn "No terminal emulator — the Container Terminal feature will not work."
fi

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
"$VENV/bin/python" -m pip install --quiet --disable-pip-version-check -r "$SCRIPT_DIR/requirements.txt" \
    || die "pip could not install the requirements (network down?). Re-run ./install.sh when online."
deps_ok || die "The Python dependencies installed but cannot be imported."
ok "Dependencies installed  ${DIM}(${VENV})${RESET}"

# ══════════════════════════════════════════════════════════════════════════════
step "  [4/6]  Setting permissions"
# ══════════════════════════════════════════════════════════════════════════════

chmod +x "$SCRIPT_DIR/docker-gui"
ok "docker-gui marked executable"

# ══════════════════════════════════════════════════════════════════════════════
step "  [5/6]  Creating the application entry"
# ══════════════════════════════════════════════════════════════════════════════

if [ "$OS" = mac ]; then
    # A minimal app bundle: shows up in Launchpad / Spotlight / ~/Applications
    APP="$HOME/Applications/Docker Control Panel.app"
    rm -rf "$APP"
    mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
    cat > "$APP/Contents/MacOS/docker-control-panel" << EOF
#!/bin/bash
exec "$SCRIPT_DIR/docker-gui" "\$@"
EOF
    chmod +x "$APP/Contents/MacOS/docker-control-panel"
    ICON_KEY=""
    if [ -f "$SCRIPT_DIR/assets/docker-icon.png" ] \
        && sips -s format icns "$SCRIPT_DIR/assets/docker-icon.png" --out "$APP/Contents/Resources/AppIcon.icns" &> /dev/null; then
        ICON_KEY="<key>CFBundleIconFile</key><string>AppIcon</string>"
        ok "App icon installed"
    else
        warn "Could not build the app icon — the app will use a generic one"
    fi
    cat > "$APP/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleExecutable</key><string>docker-control-panel</string>
  <key>CFBundleIdentifier</key><string>dev.docker-control-panel</string>
  <key>CFBundleName</key><string>Docker Control Panel</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>NSHighResolutionCapable</key><true/>
  ${ICON_KEY}
</dict></plist>
EOF
    ok "Application created  ${DIM}(~/Applications/Docker Control Panel.app)${RESET}"
else
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
Exec="$SCRIPT_DIR/docker-gui"
Icon=$ICON_DEST
Terminal=false
Categories=System;Utility;
Keywords=docker;container;management;
EOF

    chmod +x ~/.local/share/applications/docker-gui.desktop
    update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons" 2>/dev/null || true
    ok "Desktop entry created  ${DIM}(Applications → Docker Control Panel)${RESET}"
fi

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
if [ "$OS" = mac ]; then
    echo -e "    ${CYAN}1.${RESET}  Launchpad / Spotlight  →  Docker Control Panel"
else
    echo -e "    ${CYAN}1.${RESET}  Applications menu  →  Docker Control Panel"
fi
echo -e "    ${CYAN}2.${RESET}  Terminal            →  ${BOLD}docker-gui${RESET}"
echo -e "    ${CYAN}3.${RESET}  Direct              →  ${DIM}${SCRIPT_DIR}/docker-gui${RESET}"
echo
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo -e "  ${DIM}Tip: add ~/.local/bin to PATH (open a new terminal) to use 'docker-gui' in a shell.${RESET}"; echo ;;
esac
