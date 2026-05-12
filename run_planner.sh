#!/bin/bash
# Run script for Windows batch file launcher
# This runs inside WSL when called from the .bat files

cd /mnt/c/Bin/SideProjs/brightspace-weekly-planner
export PYTHONPATH=src
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-0

/home/lucca/.local/bin/python3.11 -m brightspace_planner.main "$@"
