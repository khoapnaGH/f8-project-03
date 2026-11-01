@echo off
rem ==================================================================
rem  VidGrab - Windows launcher. Bam dup file nay de chay.
rem  Lan dau: tu tao moi truong .venv va cai thu vien (can Internet).
rem ==================================================================
setlocal
chcp 65001 >nul
title VidGrab
cd /d "%~dp0"

call :find_python
if defined PY goto have_python

echo.
echo [!] Chua tim thay Python 3.10 tro len.
where winget >nul 2>nul || goto no_winget
choice /C YN /M "Tu dong cai Python 3.12 bang winget"
if errorlevel 2 goto no_winget
winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
call :find_python
if defined PY goto have_python
echo.
echo [!] Da cai Python. Hay DONG cua so nay roi bam dup run.bat mot lan nua.
pause
exit /b 1

:no_winget
echo     Tai Python tai: https://www.python.org/downloads/
echo     Khi cai, nho tick o "Add python.exe to PATH". Sau do chay lai run.bat.
start "" https://www.python.org/downloads/
pause
exit /b 1

:have_python
rem --- tao moi truong ao va cai thu vien (chi cai lai khi requirements.txt thay doi)
if not exist ".venv\Scripts\python.exe" (
  echo [*] Lan dau chay: dang tao moi truong...
  %PY% -m venv .venv
  if errorlevel 1 goto fail
)
fc /b requirements.txt ".venv\requirements.installed" >nul 2>nul
if not errorlevel 1 goto run
echo [*] Dang cai / cap nhat thu vien (1-3 phut)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
copy /y requirements.txt ".venv\requirements.installed" >nul

:run
".venv\Scripts\python.exe" app.py
echo.
echo VidGrab da dung.
pause
exit /b 0

:fail
echo.
echo [!] Cai dat that bai. Kiem tra ket noi Internet roi chay lai run.bat.
echo     Neu van loi, xoa thu muc .venv va thu lai.
pause
exit /b 1

rem ------------------------------------------------------------------
rem  Tim Python >= 3.10 (bo qua ban "python" gia cua Microsoft Store)
rem ------------------------------------------------------------------
:find_python
set "PY="
set "CHK=import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)"
py -3 -c "%CHK%" >nul 2>nul && set "PY=py -3" && exit /b 0
python -c "%CHK%" >nul 2>nul && set "PY=python" && exit /b 0
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
  if not defined PY if exist %%P %%P -c "%CHK%" >nul 2>nul && set "PY=%%~P"
)
if defined PY set PY="%PY%"
exit /b 0
