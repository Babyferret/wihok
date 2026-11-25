@echo off
rem Starts Wihok without a console window. Run setup first (see README.md).
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Wihok is not set up yet. Follow the "Set up" steps in README.md.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" main.py
