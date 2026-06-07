@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"
call "%ROOT%\scripts\ensure-env.bat" manual || goto :error

call "%ROOT%\.venv\Scripts\auto-note.exe" check "%ROOT%\articles" --append-tags
goto :done

:error
echo.
echo Failed to check articles.
pause
exit /b 1

:done
echo.
echo Done.
pause
