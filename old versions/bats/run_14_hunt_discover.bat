@echo off
cd /d "%~dp0"
echo POCKET HUNT step 1-2: build the trade table + DISCOVER on 2014-17 + 2020-21 only (and the chance yardstick)
"C:\python314\python.exe" "%~dp0asiabo_hunt.py" discover %*
echo.
pause
