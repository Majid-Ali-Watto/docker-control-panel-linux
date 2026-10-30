@echo off
rem Starts Docker Control Panel without a console window (pythonw). Run install.ps1 first.
set "ROOT=%~dp0"
if not exist "%ROOT%.venv\Scripts\pythonw.exe" (
    echo Docker Control Panel is not installed yet. Run install.bat in:
    echo   %ROOT%
    pause
    exit /b 1
)
start "" "%ROOT%.venv\Scripts\pythonw.exe" "%ROOT%docker_gui_modular.py" %*
