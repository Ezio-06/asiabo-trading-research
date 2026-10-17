@echo off
cd /d "%~dp0"

echo Running build_bars_db.py ...
"C:\python314\python.exe" "%~dp0build_bars_db.py"

echo.
echo Done.
pause
