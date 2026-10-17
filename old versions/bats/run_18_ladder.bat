@echo off
cd /d "%~dp0"
echo THE LADDER TRADE: 6 synthetic worlds + the real data (resumable, about 25-35 min)
"C:\python314\python.exe" "%~dp0asiabo_ladder.py" %*
echo.
pause
