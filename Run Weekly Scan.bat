@echo off
REM ============================================================
REM  Brightspace Weekly Planner — Double-click to run
REM  Runs the weekly scan inside WSL (headed browser mode)
REM ============================================================

echo Opening Brightspace Weekly Planner...

REM Launch WSL in a new terminal window with the scan command.
REM The browser will appear on your desktop via WSLg.
start "" wsl.exe -- bash -c "cd /mnt/c/Bin/SideProjs/brightspace-weekly-planner && export PYTHONPATH=src && export DISPLAY=:0 && export WAYLAND_DISPLAY=wayland-0 && /home/lucca/.local/bin/python3.11 -m brightspace_planner.main scan 2>&1; echo ''; echo '--- Scan complete. Press Enter to close this window.---'; read"

REM After a short delay, open the dashboard in the default browser
ping -n 6 127.0.0.1 >nul 2>&1
if exist "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html" (
    start "" "C:\Bin\SideProjs\brightspace-weekly-planner\output\dashboard.html"
)
