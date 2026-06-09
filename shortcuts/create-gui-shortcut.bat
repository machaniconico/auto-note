@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\create-gui-shortcut.ps1" ^
  -ProjectDir "%ROOT%" ^
  -ShortcutPath "%ROOT%\auto-note.lnk" ^
  -SafeDisplayShortcutPath "%ROOT%\auto-note safe display.lnk" || goto :error
goto :done

:error
echo.
echo Failed to create shortcut.
pause
exit /b 1

:done
echo.
echo Shortcut created.
pause
