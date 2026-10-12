@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create the virtual environment and install requirements first. See README.md.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8765"
".venv\Scripts\python.exe" app.py
pause
