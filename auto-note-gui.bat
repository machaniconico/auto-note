@echo off
setlocal

cd /d "%~dp0"
set "ROOT=%~dp0."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
if not exist "%ROOT%\.auto-note" mkdir "%ROOT%\.auto-note"
set "LOG=%ROOT%\.auto-note\gui-error.log"
set "GUI_DISPLAY_ARG="
set "GUI_DISPLAY_LABEL=normal"

if /I "%~1"=="--safe-display" (
  set "GUI_DISPLAY_ARG=--safe-display"
  set "GUI_DISPLAY_LABEL=safe display"
)
if /I "%~1"=="/safe-display" (
  set "GUI_DISPLAY_ARG=--safe-display"
  set "GUI_DISPLAY_LABEL=safe display"
)
if /I "%AUTO_NOTE_SAFE_DISPLAY%"=="1" (
  set "GUI_DISPLAY_ARG=--safe-display"
  set "GUI_DISPLAY_LABEL=safe display"
)

echo Preparing auto-note GUI... > "%LOG%"
echo Display mode: %GUI_DISPLAY_LABEL% >> "%LOG%"
call "%ROOT%\scripts\ensure-env.bat" manual >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo Checking auto-note GUI startup... >> "%LOG%"
call "%ROOT%\.venv\Scripts\python.exe" -m auto_note gui --project-dir "%ROOT%" --smoke %GUI_DISPLAY_ARG% >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo Starting auto-note GUI... >> "%LOG%"
call "%ROOT%\.venv\Scripts\python.exe" -m auto_note gui --project-dir "%ROOT%" %GUI_DISPLAY_ARG% >> "%LOG%" 2>&1
if errorlevel 1 goto :error

exit /b 0

:error
if exist "%ROOT%\.venv\Scripts\python.exe" (
  echo Running startup recovery kit... >> "%LOG%"
  call "%ROOT%\.venv\Scripts\python.exe" -m auto_note recovery-kit --project-dir "%ROOT%" --report >> "%LOG%" 2>&1
)
echo.
echo Failed to start auto-note GUI.
echo.
echo Next steps:
echo 1. Check the log file: "%LOG%"
echo 2. Check the newest recovery report in:
echo    "%ROOT%\.auto-note\reports"
echo 3. Run the recovery kit again if needed:
echo    "%ROOT%\.venv\Scripts\python.exe" -m auto_note recovery-kit --project-dir "%ROOT%" --report
echo 4. If created, send the newest zip in:
echo    "%ROOT%\.auto-note\support"
echo 5. Run this GUI check:
echo    "%ROOT%\.venv\Scripts\python.exe" -m auto_note gui --project-dir "%ROOT%" --smoke
echo 6. If the screen text is hard to read, try safe display mode:
echo    "%ROOT%\.venv\Scripts\python.exe" -m auto_note gui --project-dir "%ROOT%" --safe-display
echo    or run: auto-note-gui.bat --safe-display
echo 7. Create a support bundle manually:
echo    "%ROOT%\.venv\Scripts\python.exe" -m auto_note support --project-dir "%ROOT%" --bundle
echo.
echo Log:
type "%LOG%"
echo.
pause
exit /b 1
