@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"
call "%ROOT%\scripts\ensure-env.bat" manual || goto :error

set "ARTICLE=%~1"
if "%ARTICLE%"=="" set "ARTICLE=%ROOT%\articles\post.md"

call "%ROOT%\.venv\Scripts\auto-note.exe" copy "%ARTICLE%" --part body --append-tags
goto :done

:error
echo.
echo Failed to copy article body.
pause
exit /b 1

:done
echo.
echo Copied.
pause
