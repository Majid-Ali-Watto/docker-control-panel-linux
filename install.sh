#!/bin/bash
# Docker Control Panel - Installation Script

echo "🐳 Docker Control Panel - Installation"
echo "======================================"
echo

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✓ Python 3 found"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker is not installed. You'll need Docker to use this application."
    echo "   Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ Docker found"
fi

# Verify project structure
if [ ! -d "$SCRIPT_DIR/src" ]; then
    echo "❌ Error: src directory not found. Project structure may be incomplete."
    exit 1
fi

required_dirs=("src/config" "src/docker" "src/ui" "src/help" "src/utils")
for dir in "${required_dirs[@]}"; do
    if [ ! -d "$SCRIPT_DIR/$dir" ]; then
        echo "❌ Error: $dir directory not found. Project structure is incomplete."
        exit 1
    fi
done
echo "✓ Project structure verified"

# Make the main script executable
chmod +x "$SCRIPT_DIR/docker-gui"
echo "✓ Made docker-gui executable"

# Create desktop entry
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/docker-gui.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Docker Control Panel
Comment=GUI for Docker container management
Exec=$SCRIPT_DIR/docker-gui
Icon=docker
Terminal=false
Categories=System;Utility;
Keywords=docker;container;management;
EOF

chmod +x ~/.local/share/applications/docker-gui.desktop
echo "✓ Created desktop entry"

# Update desktop database
update-desktop-database ~/.local/share/applications/ 2>/dev/null || true

# Create symlink in ~/.local/bin for command-line access
mkdir -p ~/.local/bin
ln -sf "$SCRIPT_DIR/docker-gui" ~/.local/bin/docker-gui 2>/dev/null || true
echo "✓ Created command-line shortcut"

echo
echo "✅ Installation complete!"
echo
echo "You can now run the application:"
echo "  1. From Applications menu: Search for 'Docker Control Panel'"
echo "  2. From terminal: docker-gui"
echo "  3. Directly: $SCRIPT_DIR/docker-gui"
echo
echo "Note: Make sure ~/.local/bin is in your PATH for command-line access."
