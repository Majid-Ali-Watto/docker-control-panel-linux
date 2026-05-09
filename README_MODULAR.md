# Docker GUI - Modular Architecture

This project has been refactored following **DRY (Don't Repeat Yourself)** and **SOC (Separation of Concerns)** principles.

## 📁 Project Structure

```
docker-ui-modular/
├── docker_gui.py              # Original monolithic file (kept for reference)
├── docker_gui_modular.py      # NEW: Main application entry point
├── config_manager.py          # Configuration and password management
├── config_themes.py           # Theme configurations
├── config_menu.py             # Menu structure configuration
├── utils.py                   # Common utility functions
├── docker_operations.py       # Core Docker command execution
├── docker_actions.py          # High-level Docker actions (start/stop/etc)
├── docker_tables.py           # Functions to display Docker resources
├── docker_gui_features.py     # Complex dialogs and specialized features
├── ui_components.py           # Reusable UI components and dialogs
├── ui_display.py              # Display manager for tables and text
├── keyboard_navigation.py     # Keyboard navigation utilities
├── help_commands.py           # Docker commands help text
├── help_info.py               # General help information
└── README_MODULAR.md          # This file
```

## 🏗️ Module Descriptions

### Core Application
- **`docker_gui_modular.py`**: Main application class and entry point. Orchestrates all modules.

### Configuration Modules
- **`config_manager.py`**: Handles application settings and password storage
  - Password loading/saving/deletion
  - Configuration file management
  
- **`config_themes.py`**: Theme definitions and configurations
- **`config_menu.py`**: Menu structure and organization

### Utility Modules
- **`utils.py`**: Common utility functions
  - Docker installation checks
  - Command execution (sync/async)
  - Fixed-width table parsing
  
### Docker Operation Modules
- **`docker_operations.py`**: Core Docker command execution
  - Basic command wrappers
  - Table command execution
  
- **`docker_actions.py`**: High-level Docker actions
  - Service control (start/stop/restart)
  - Container operations (start/stop/delete all)
  - Image operations (delete all)
  - Volume operations (prune)
  - Resource cleanup
  
- **`docker_tables.py`**: Display Docker resources in tables
  - Container listings (all/running/stopped/stats)
  - Image listings (all/used/unused)
  - Volume listings
  - Disk usage views

### UI Modules
- **`ui_components.py`**: Reusable UI components
  - Password dialogs
  - Docker installation prompts
  - Table widget creation
  
- **`ui_display.py`**: Display manager class
  - Table display with search
  - Text output display
  - Action button management
  
- **`keyboard_navigation.py`**: Keyboard navigation utilities
  - Tab navigation setup
  - Focus management
  - Keyboard shortcuts

### Feature Modules
- **`docker_gui_features.py`**: Complex features and dialogs
  - Pull image dialog
  - Container terminal dialog
  - Container logs viewer
  - Disk usage viewer
  - Context menus
  - Selected item actions

### Help Modules
- **`help_commands.py`**: Docker commands reference
- **`help_info.py`**: General application help

## 🎯 Design Patterns Applied

### 1. **Separation of Concerns (SOC)**
Each module has a single, well-defined responsibility:
- Configuration separate from business logic
- UI separate from data operations
- Docker operations isolated from display logic

### 2. **Don't Repeat Yourself (DRY)**
- Common functions extracted to utility modules
- Reusable UI components
- Shared Docker command patterns
- Single source of truth for configurations

### 3. **Dependency Injection**
- Callbacks passed as parameters
- Display manager receives widget references
- Action functions receive display callbacks

### 4. **Class-Based Architecture**
- `DockerGUI` main application class
- `DisplayManager` for output management
- Clear state management

## 🚀 Usage

### Running the Modular Version
```bash
python3 docker_gui_modular.py
```

### Running the Original Version
```bash
python3 docker_gui.py
```

## 🔧 Benefits of Modular Structure

1. **Maintainability**: Easier to locate and fix bugs
2. **Testability**: Individual modules can be tested in isolation
3. **Reusability**: Components can be reused in other projects
4. **Scalability**: Easy to add new features without affecting existing code
5. **Readability**: Smaller, focused files are easier to understand
6. **Collaboration**: Multiple developers can work on different modules

## 📊 Module Dependencies

```
docker_gui_modular.py
├── config_manager.py
├── config_themes.py
├── config_menu.py
├── utils.py
├── docker_operations.py
│   └── utils.py
├── docker_actions.py
│   ├── utils.py
│   └── config_manager.py
├── docker_tables.py
│   ├── docker_operations.py
│   ├── docker_actions.py
│   └── utils.py
├── docker_gui_features.py
│   ├── utils.py
│   ├── config_manager.py
│   ├── docker_actions.py
│   └── ui_components.py
├── ui_components.py
│   ├── config_manager.py
│   └── keyboard_navigation.py
├── ui_display.py
├── keyboard_navigation.py
├── help_commands.py
└── help_info.py
```

## 🔄 Migration Notes

The original `docker_gui.py` (1843 lines) has been split into:
- 9 new focused modules (average ~200-300 lines each)
- 1 main application file (~500 lines)
- Existing config files remain unchanged

Total reduction in complexity through modularization while maintaining all functionality.

## 🐛 Testing

Each module can be tested independently:
```python
# Test utilities
from utils import check_docker_installed
assert check_docker_installed() in [True, False]

# Test configuration
from config_manager import load_saved_password
password = load_saved_password()  # Returns None if not saved

# Test Docker operations
from docker_actions import check_docker_running
status = check_docker_running()
```

## 📝 Future Improvements

1. Add unit tests for each module
2. Create interface abstractions for easier mocking
3. Implement logging throughout modules
4. Add configuration validation
5. Create plugin system for extensibility

## 🤝 Contributing

When adding new features:
1. Identify the appropriate module based on responsibility
2. Create new module if feature doesn't fit existing categories
3. Update this README with new module information
4. Keep modules focused and cohesive

## 📄 License

Same as original project.
