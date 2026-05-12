@echo off
REM ============================================================
REM  Brightspace Weekly Planner — DEEP SCAN
REM  Expands all accordion trees and reads every content page
REM ============================================================

echo Starting Brightspace Weekly Planner — DEEP SCAN...
echo This will expand all accordions and visit every content page.
echo.

start "" wsl.exe -- bash -c "cd /mnt/c/Bin/SideProjs/brightspace-weekly-planner && export PYTHONPATH=src && export DISPLAY=:0 && export WAYLAND_DISPLAY=wayland-0 && /home/lucca/.local/bin/python3.11 -m brightspace_planner.main deep-scan 2>&1; echo ''; echo '--- Deep scan complete. Press Enter to close this window.---'; read"
