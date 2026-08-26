@echo off
rem start-streamlit.bat - start Streamlit debug UI (http://127.0.0.1:8501)
rem Double-click or run in cmd; it invokes the .ps1 with ExecutionPolicy Bypass.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-streamlit.ps1"
pause
