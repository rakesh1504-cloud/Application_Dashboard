@echo off
REM Double-click to set up and start the Case Management System on Windows.
cd /d "%~dp0"
if not exist .venv (
    echo Setting up for the first time...
    python -m venv .venv || (echo Python is not installed. Get it from https://www.python.org/downloads/ & pause & exit /b 1)
    .venv\Scripts\python -m pip install -r requirements.txt
)
.venv\Scripts\python run.py
pause
