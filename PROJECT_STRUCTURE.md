# Docker UI Modular - Project Structure

## Directory Organization

The project has been organized into a modular structure for better maintainability:

```
docker-ui-modular/
├── docker_gui_modular.py          # Main entry point
├── docker-gui                      # Executable script
├── install.sh                      # Installation script
├── README.md                       # Main documentation
├── README_MODULAR.md              # Modular architecture docs
└── src/                           # Source code package
    ├── config/                    # Configuration modules
    │   ├── __init__.py
    │   ├── config_manager.py      # Password and config management
    │   ├── config_menu.py         # Menu structure definition
    │   └── config_themes.py       # UI themes configuration
    │
    ├── docker/                    # Docker-related modules
    │   ├── __init__.py
    │   ├── docker_actions.py      # High-level Docker actions
    │   ├── docker_commands_constants.py  # Command constants
    │   ├── docker_gui_features.py # Complex Docker features
    │   ├── docker_operations.py   # Core Docker operations
    │   └── docker_tables.py       # Docker table displays
    │
    ├── ui/                        # UI components
    │   ├── __init__.py
    │   ├── keyboard_navigation.py # Keyboard navigation
    │   ├── ui_components.py       # Reusable UI widgets
    │   └── ui_display.py          # Display management
    │
    ├── help/                      # Documentation modules
    │   ├── __init__.py
    │   ├── help_commands.py       # Command documentation
    │   └── help_info.py           # General help info
    │
    └── utils/                     # Utility modules
        ├── __init__.py
        ├── threads.py             # Threading utilities
        └── utils.py               # Common utilities
```

## Module Purposes

### Config (`src/config/`)
- **config_manager.py**: Handles password storage and configuration management
- **config_menu.py**: Defines the menu structure and categories
- **config_themes.py**: Contains UI theme definitions and color schemes

### Docker (`src/docker/`)
- **docker_actions.py**: High-level actions (start/stop containers, clean resources)
- **docker_commands_constants.py**: Docker command templates and constants
- **docker_gui_features.py**: Complex features (pull images, terminals, logs, disk usage)
- **docker_operations.py**: Core Docker command execution
- **docker_tables.py**: Functions to display Docker resources in tables

### UI (`src/ui/`)
- **ui_components.py**: Reusable UI components and dialogs
- **ui_display.py**: Display manager for tables and text output
- **keyboard_navigation.py**: Keyboard navigation and shortcuts

### Help (`src/help/`)
- **help_commands.py**: Docker command documentation
- **help_info.py**: General help information

### Utils (`src/utils/`)
- **utils.py**: Common utility functions
- **threads.py**: Threading utilities for async operations

## Benefits of This Structure

1. **Better Organization**: Related files are grouped together
2. **Easier Navigation**: Clear separation of concerns
3. **Improved Maintainability**: Each module has a specific purpose
4. **Scalability**: Easy to add new features to appropriate directories
5. **Cleaner Imports**: Package structure makes dependencies clear

## Usage

The application works the same way as before:

```bash
# Run directly
./docker-gui

# Or with Python
python3 docker_gui_modular.py

# Install (if not already installed)
./install.sh
```

All imports have been updated to reflect the new structure using the `src` package prefix.
