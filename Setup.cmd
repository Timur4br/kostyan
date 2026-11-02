@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing. Create it with: py -3 -m venv .venv
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\setup.py
pause
