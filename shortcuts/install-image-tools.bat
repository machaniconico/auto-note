@echo off
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"

call "%ROOT%\scripts\ensure-env.bat" manual || goto :error
call "%ROOT%\.venv\Scripts\python.exe" -m pip install -e "%ROOT%[images]" || goto :error

echo.
echo Image optimization tools installed.
pause
exit /b 0

:error
echo.
echo Failed to install image optimization tools.
pause
exit /b 1
