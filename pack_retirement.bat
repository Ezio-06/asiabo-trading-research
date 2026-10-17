@echo off
rem pack_retirement.bat -- builds the retirement box. Copies only; never moves or deletes an original file.
rem Box = code + launcher + notes + text reports + small logs. Left out: bars.db, bars_origin, synth, exam dbs,
rem the big .csv / .json trade tables in reports (they stay in this folder).
cd /d "%~dp0"
set BOX=retirement_box
set ZIP=asiabo_retired_2026-10-16.zip

if exist "%BOX%" (
  echo "%BOX%" already exists. Rename or remove it first, then run this again.
  pause
  exit /b 1
)
if exist "%ZIP%" (
  echo "%ZIP%" already exists. Rename or remove it first, then run this again.
  pause
  exit /b 1
)

mkdir "%BOX%"
echo Copying scripts and top-level files...
for %%F in (*.py run.bat modules.json runs.csv build_bars_db_log.txt gaps_to_check.csv README.md RETIREMENT.md pack_retirement.bat) do (
  if exist "%%F" copy /y "%%F" "%BOX%\" >nul
)

echo Copying notes, old versions, text reports and exam markers...
robocopy "docs" "%BOX%\docs" /E /NFL /NDL /NJH /NJS /NP >nul
robocopy "old versions" "%BOX%\old versions" /E /NFL /NDL /NJH /NJS /NP >nul
robocopy "reports" "%BOX%\reports" *.txt /S /NFL /NDL /NJH /NJS /NP >nul
robocopy "exam_hold" "%BOX%\exam_hold" *_DONE.txt /NFL /NDL /NJH /NJS /NP >nul

echo Zipping...
powershell -NoProfile -Command "Compress-Archive -Path '%BOX%\*' -DestinationPath '%ZIP%'"
if errorlevel 1 (
  echo Zipping failed. The copied files are still in "%BOX%".
  pause
  exit /b 1
)

for %%A in ("%ZIP%") do echo Done: %ZIP% ^(%%~zA bytes^). The "%BOX%" folder holds the same files unzipped.
pause
