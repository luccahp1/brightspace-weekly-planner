@echo off
REM ============================================================
REM  Brightspace Weekly Planner — GUI Test
REM  Double-click to test the browser appears on desktop
REM ============================================================
title Brightspace Weekly Planner — GUI Test

echo.
echo   ============================================
echo     Brightspace Weekly Planner
echo     GUI Test
echo   ============================================
echo.
echo   This will open a Chromium window on your
echo   desktop to verify the browser works.
echo.

wsl.exe --cd C:\Bin\SideProjs\brightspace-weekly-planner -- bash run_planner.sh gui-test

echo.
pause
