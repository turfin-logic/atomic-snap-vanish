@echo off
title Atomic Snap Vanish - Setup
echo ========================================
echo  ATOMIC SNAP VANISH - First-time setup
echo ========================================
echo.
echo Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Done! Now double-click run.bat to start.
echo (Optional: install OBS Studio for Zoom/Meet virtual camera - see README)
pause
