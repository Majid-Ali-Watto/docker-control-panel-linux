#!/usr/bin/env python3
"""Test if all imports work correctly (ASCII output: Windows consoles are often cp1252)"""

import sys
import traceback

try:
    from docker_gui_modular import DockerGUI  # noqa: F401
except Exception as e:
    print(f"FAIL: import error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("OK: all imports successful")
print("OK: directory structure is working correctly")
