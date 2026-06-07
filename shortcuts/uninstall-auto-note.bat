@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\uninstall-auto-note.ps1" -InstallDir "%ROOT%" || goto :error
goto :done

:error
echo.
echo Failed to uninstall auto-note.
pause
exit /b 1

:done
echo.
echo auto-note uninstalled. Articles and settings were kept unless you used -RemoveUserData.
pause
