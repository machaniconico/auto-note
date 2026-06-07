@echo off
setlocal

cd /d "%~dp0.."

set "MODE=%~1"
if "%MODE%"=="" set "MODE=browser"
set "READY_FILE=.venv\.auto-note-browser-ready.txt"
set "INSTALL_TARGET=.[browser]"
if /i "%MODE%"=="manual" (
  set "READY_FILE=.venv\.auto-note-manual-ready.txt"
  set "INSTALL_TARGET=."
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 python -m venv .venv
  if errorlevel 1 exit /b 1
)

if not exist "%READY_FILE%" goto :install_package
if not exist ".venv\Scripts\auto-note.exe" goto :install_package
goto :package_ready

:install_package
echo Installing auto-note dependencies...
call ".venv\Scripts\python.exe" -m pip install -e "%INSTALL_TARGET%"
if errorlevel 1 exit /b 1
echo ready> "%READY_FILE%"

:package_ready

if /i "%MODE%"=="manual" exit /b 0

if not exist ".auto-note" mkdir ".auto-note"
if not exist ".auto-note\chromium-ready.txt" (
  echo Installing Playwright Chromium...
  call ".venv\Scripts\python.exe" -m playwright install chromium
  if errorlevel 1 exit /b 1
  echo ready> ".auto-note\chromium-ready.txt"
)

exit /b 0
