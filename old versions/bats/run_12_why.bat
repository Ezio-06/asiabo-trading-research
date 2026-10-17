@echo off
cd /d "%~dp0"
echo ============================================================
echo  WHY PHASE  step 1 of 2: the frozen book on the REAL bars.db
echo ============================================================
"C:\python314\python.exe" "%~dp0asiabo_why.py" all
echo.
echo ============================================================
echo  step 2 of 2: the same on a DAY-SHUFFLED cousin (yardstick:
echo  real days, real costs, no multi-day structure). ~1.5 GB temp
echo ============================================================
"C:\python314\python.exe" "%~dp0make_synth.py" gen --preset dayshuffle --seed 1 --out "synth\why_dayshuffle_s1.db"
"C:\python314\python.exe" "%~dp0asiabo_why.py" all --db "synth\why_dayshuffle_s1.db"
if exist "synth\why_dayshuffle_s1.db" del "synth\why_dayshuffle_s1.db"
echo.
echo done. Both reports are in 'claude vision' (why.txt and why_synth_dayshuffle_s1.txt).
pause
