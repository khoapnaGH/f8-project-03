@echo off
chcp 65001 >nul
title VidGrab
cd /d "%~dp0"
where python >nul 2>nul || (echo [!] Chua cai Python. Tai tai https://www.python.org/downloads/ ^(tick "Add Python to PATH"^) & pause & exit /b)
if not exist ".venv\Scripts\python.exe" (
  echo [*] Lan dau chay: dang tao moi truong va cai thu vien...
  python -m venv .venv || (pause & exit /b)
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (pause & exit /b)
)
".venv\Scripts\python.exe" app.py
pause
