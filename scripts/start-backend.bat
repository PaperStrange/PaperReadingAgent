@echo off
rem start-backend.bat - start FastAPI backend (http://127.0.0.1:8787)
rem Double-click or run in cmd; it invokes the .ps1 with ExecutionPolicy Bypass.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-backend.ps1"
pause
