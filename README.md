# Docker Control Panel

A comprehensive GUI application for managing Docker containers, images, volumes, and monitoring stats on Linux.

## Features

- 🐳 **Docker Service Control**: Start, stop, restart Docker service
- 📦 **Container Management**: View, start, stop, delete containers
- 🖼️ **Image Management**: View, pull, delete images; distinguish used/unused images
- 💾 **Volume Management**: View and manage Docker volumes
- 📊 **Statistics**: Real-time container stats and disk usage
- 💻 **Container Terminal**: Interactive shell access to containers
- 📄 **Log Viewer**: View container logs with live follow capability
- 🎨 **Themes**: 5 different themes (Default, Dark, Light Alt, Classic, Clam Light)
- 🔍 **Search**: Filter tables across all categories
- 🔐 **Password Management**: Securely save sudo password
- 📋 **Copy/Paste**: Right-click context menus for easy data copying

## Installation

### Quick Install

```bash
cd /home/majid-ali/Documents/Learning/docker-ui
./install.sh
```

### Manual Setup

1. Make the script executable:
```bash
chmod +x docker-gui
```

2. Run the application:
```bash
./docker-gui
```

## Running the Application

After installation, you can run it in three ways:

1. **From Applications Menu**: Search for "Docker Control Panel"
2. **From Terminal**: `docker-gui` (if ~/.local/bin is in PATH)
3. **Directly**: `/home/majid-ali/Documents/Learning/docker-ui/docker-gui`

## Requirements

- Python 3.x
- Tkinter (usually included with Python)
- Docker
- Sudo access (for Docker commands)

## Usage

1. Launch the application
2. Enter your sudo password (can be saved for future sessions)
3. Select a category from the sidebar (Docker, Containers, Images, Volumes, Stats)
4. Use action buttons to perform operations
5. Select items from tables to perform bulk actions

### Container Features

- **Start/Stop/Delete**: Select containers and use action buttons
- **Open Terminal**: Execute commands inside containers
- **View Logs**: See container logs with live follow option

### Image Features

- **Pull Images**: Download images from Docker Hub
- **View Used/Unused**: See which images are in use
- **Run Containers**: Create containers from images

### Help & Commands

- Commands tab: Lists all Docker commands used
- Help tab: Comprehensive guide for all features

## File Structure

```
docker-ui/
├── docker_gui.py          # Main application
├── docker-gui             # Executable launcher
├── install.sh             # Installation script
└── README.md              # This file
```

## Creating a Standalone Executable (Optional)

If you want a true standalone executable, you can use PyInstaller:

```bash
# Install PyInstaller (use pipx or virtual environment)
pipx install pyinstaller

# Create executable
pyinstaller --onefile --windowed --name="docker-gui" docker_gui.py

# The executable will be in dist/docker-gui
```

## Security

- Passwords are stored in `~/.docker-gui/config.json` with 0600 permissions
- Only the user can read the password file
- Password can be changed or deleted from the application

## Uninstallation

To remove the application:

```bash
# Remove desktop entry
rm ~/.local/share/applications/docker-gui.desktop
rm ~/.local/bin/docker-gui

# Remove config (optional)
rm -rf ~/.docker-gui/

# Update desktop database
update-desktop-database ~/.local/share/applications/
```

## License

Free to use and modify.

## Author

Created for easy Docker management on Linux systems.
