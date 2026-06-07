@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"
call "%ROOT%\scripts\ensure-env.bat" manual || goto :error

if "%~1"=="" (
  call "%ROOT%\.venv\Scripts\auto-note.exe" menu --project-dir "%ROOT%"
) else (
  call "%ROOT%\.venv\Scripts\auto-note.exe" menu --project-dir "%ROOT%" --file "%~1"
)
goto :done

:error
echo.
echo Failed to start auto-note.
pause
exit /b 1

:done
endlocal
