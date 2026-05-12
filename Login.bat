@echo off
REM ============================================================
REM  Brightspace Weekly Planner — Login / MFA Setup
REM  Double-click to log in and save your session
REM ============================================================
title Brightspace Weekly Planner — Login

echo.
echo   ============================================
echo     Brightspace Weekly Planner
echo     Login / MFA Setup
echo   ============================================
echo.
echo   A Chromium window will open on your desktop.
echo   Please log in and complete MFA.
echo.

wsl.exe --cd C:\Bin\SideProjs\brightspace-weekly-planner -- bash run_planner.sh auth

echo.
pause
