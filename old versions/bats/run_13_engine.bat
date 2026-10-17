@echo off
cd /d "%~dp0"
echo POCKET ENGINE stage 1: ideal and nightmare worlds (resumable: double-click again if stopped)
"C:\python314\python.exe" "%~dp0asiabo_engine.py" %*
echo.
pause
