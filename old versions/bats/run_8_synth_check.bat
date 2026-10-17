@echo off
cd /d "%~dp0"
"C:\python314\python.exe" "%~dp0make_synth.py" %*
echo.
pause
