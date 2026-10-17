@echo off
cd /d "%~dp0"
echo REGIME ENGINE: worlds with a known momentum / neutral / snap-back truth (resumable: double-click again if stopped)
"C:\python314\python.exe" "%~dp0asiabo_regime.py" %*
echo.
pause
