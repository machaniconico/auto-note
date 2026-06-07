@echo off
setlocal

cd /d "%~dp0"
set "ROOT=%~dp0."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
if not exist "%ROOT%\.auto-note" mkdir "%ROOT%\.auto-note"
set "LOG=%ROOT%\.auto-note\gui-error.log"

echo Preparing auto-note GUI... > "%LOG%"
call "%ROOT%\scripts\ensure-env.bat" manual >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo Checking auto-note GUI startup... >> "%LOG%"
call "%ROOT%\.venv\Scripts\python.exe" -m auto_note gui --project-dir "%ROOT%" --smoke >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo Starting auto-note GUI... >> "%LOG%"
call "%ROOT%\.venv\Scripts\python.exe" -m auto_note gui --project-dir "%ROOT%" >> "%LOG%" 2>&1
if errorlevel 1 goto :error

exit /b 0

:error
if exist "%ROOT%\.venv\Scripts\python.exe" (
  echo Creating startup support bundle... >> "%LOG%"
  call "%ROOT%\.venv\Scripts\python.exe" -m auto_note support --project-dir "%ROOT%" --bundle >> "%LOG%" 2>&1
)
echo.
echo Failed to start auto-note GUI.
echo.
echo Next steps:
echo 1. Check the log file: "%LOG%"
echo 2. If created, send the newest zip in:
echo    "%ROOT%\.auto-note\support"
echo 3. Run this GUI check:
echo    "%ROOT%\.venv\Scripts\python.exe" -m auto_note gui --project-dir "%ROOT%" --smoke
echo 4. Create a support bundle manually:
echo    "%ROOT%\.venv\Scripts\python.exe" -m auto_note support --project-dir "%ROOT%" --bundle
echo.
echo Log:
type "%LOG%"
echo.
pause
exit /b 1
