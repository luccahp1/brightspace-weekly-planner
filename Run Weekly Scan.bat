@echo off
REM ============================================================
REM  Brightspace Weekly Planner — Weekly Scan
REM  Double-click to run from Windows Explorer
REM ============================================================
title Brightspace Weekly Planner — Weekly Scan

echo.
echo   ============================================
echo     Brightspace Weekly Planner
echo     Weekly Scan
echo   ============================================
echo.
echo   The scan will open a Chromium window on your
echo   desktop via WSLg. If your session has expired
echo   you will be asked to log in and complete MFA.
echo.

if not exist "C:\Bin\SideProjs\brightspace-weekly-planner\src\brightspace_planner\main.py" (
    echo   ERROR: Project folder not found.
    echo   Make sure this .bat file is in the same folder
    echo   as the brightspace-weekly-planner project.
    echo.
    pause
    exit /b 1
)

echo   Starting scan...
echo.

wsl.exe --cd C:\Bin\SideProjs\brightspace-weekly-planner -- bash run_planner.sh scan

echo.
if exist "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html" (
    echo   Opening dashboard...
    start "" "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html"
) else (
    echo   NOTE: dashboard.html was not created.
    echo   Check the output above for errors.
)

echo.
pause
