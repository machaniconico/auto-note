@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"
call "%ROOT%\scripts\ensure-env.bat" manual || goto :error

set "ARTICLE=%~1"
if "%ARTICLE%"=="" set "ARTICLE=%ROOT%\articles\post.md"

echo Preparing note article for publishing:
echo %ARTICLE%
echo.
echo The normal browser will open note.com and a copy helper.
echo Paste the title/body, then click publish in note.com.

call "%ROOT%\.venv\Scripts\auto-note.exe" manual "%ARTICLE%" --append-tags
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
