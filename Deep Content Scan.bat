@echo off
REM ============================================================
REM  Brightspace Weekly Planner — Deep Content Scan
REM  Double-click to run from Windows Explorer
REM ============================================================
title Brightspace Weekly Planner — Deep Content Scan

echo.
echo   ============================================
echo     Brightspace Weekly Planner
echo     Deep Content Scan
echo   ============================================
echo.
echo   This will expand every accordion tree in every
echo   course and read every content page. It may take
echo   several minutes.
echo.
echo   A Chromium window will appear on your desktop.
echo.

if not exist "C:\Bin\SideProjs\brightspace-weekly-planner\src\brightspace_planner\main.py" (
    echo   ERROR: Project folder not found.
    pause
    exit /b 1
)

wsl.exe --cd C:\Bin\SideProjs\brightspace-weekly-planner -- bash run_planner.sh deep-scan

echo.
if exist "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html" (
    echo   Opening dashboard...
    start "" "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html"
)

echo.
pause
