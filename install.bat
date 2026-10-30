@echo off
rem Double-click (or run) to install Docker Control Panel on Windows. See install.ps1.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 pause
