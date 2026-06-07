@echo off
setlocal

echo Opening note.com login...
start "" "https://note.com/login"
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
