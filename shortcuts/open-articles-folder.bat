@echo off
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
start "" "%ROOT%\articles"
