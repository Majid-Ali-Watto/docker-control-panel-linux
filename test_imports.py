#!/usr/bin/env python3
"""Test if all imports work correctly"""

try:
    from docker_gui_modular import DockerGUI
    print("✓ All imports successful!")
    print("✓ Directory structure is working correctly")
except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
