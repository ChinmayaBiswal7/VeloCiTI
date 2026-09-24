@echo off
cd /d "%~dp0city flow model"
if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" server_standalone.py
) else (
    python server_standalone.py
)
