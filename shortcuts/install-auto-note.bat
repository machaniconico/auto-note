@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\install-auto-note.ps1" || goto :error
goto :done

:error
echo.
echo Failed to install auto-note.
pause
exit /b 1

:done
echo.
echo auto-note installed.
pause
