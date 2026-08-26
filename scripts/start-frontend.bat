@echo off
rem start-frontend.bat - start frontend dev server (http://127.0.0.1:5173)
rem Double-click or run in cmd; it invokes the .ps1 with ExecutionPolicy Bypass.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-frontend.ps1"
pause
