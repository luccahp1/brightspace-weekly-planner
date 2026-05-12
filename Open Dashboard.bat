@echo off
REM ============================================================
REM  Brightspace Weekly Planner — Open Dashboard
REM  Double-click to regenerate and open the dashboard
REM ============================================================
title Brightspace Weekly Planner — Dashboard

echo.
echo   Opening dashboard...
echo.

if exist "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html" (
    start "" "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html"
) else (
    echo   Dashboard not found. Generating from latest data...
    echo.
    wsl.exe --cd C:\Bin\SideProjs\brightspace-weekly-planner -- bash run_planner.sh dashboard
    echo.
    if exist "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html" (
        start "" "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html"
    ) else (
        echo   ERROR: Could not generate dashboard.
        echo   Run a scan first.
    )
)

echo.
pause
