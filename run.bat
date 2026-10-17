@echo off
cd /d "%~dp0"
"C:\python314\python.exe" "%~dp0asiabo.py" %*
if not "%~1"=="" pause
