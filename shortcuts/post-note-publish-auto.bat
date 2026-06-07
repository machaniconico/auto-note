@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"
call "%ROOT%\scripts\ensure-env.bat" || goto :error

set "ARTICLE=%~1"
if "%ARTICLE%"=="" set "ARTICLE=%ROOT%\articles\post.md"

echo Publishing note article with automated browser:
echo %ARTICLE%
echo.
echo This mode only works if login succeeded inside the automated browser.
echo Close this window now if you did not mean to publish.
timeout /t 5 /nobreak >nul

call "%ROOT%\.venv\Scripts\auto-note.exe" post "%ARTICLE%" --publish --append-tags --close-after-fill --browser msedge
goto :done

:error
echo.
echo Failed to prepare auto-note.
pause
exit /b 1

:done
echo.
echo Done.
pause
