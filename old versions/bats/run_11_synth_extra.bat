@echo off
cd /d "%~dp0"
"C:\python314\python.exe" "%~dp0synth_batch.py" --presets longblock %*
echo.
pause
