@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"
call "%ROOT%\scripts\ensure-env.bat" manual || goto :error

set "TITLE=%~1"
if "%TITLE%"=="" (
  set /p "TITLE=Article title: "
)
if "%TITLE%"=="" goto :error

call "%ROOT%\.venv\Scripts\auto-note.exe" new "%TITLE%" --open
goto :done

:error
echo.
echo Failed to create a new article.
pause
exit /b 1

:done
echo.
echo Done.
pause
