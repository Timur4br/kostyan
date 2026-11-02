@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" scripts\database.py stop
pause
