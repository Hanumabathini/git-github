@echo off
REM Renders every video in shorts.json with WanGP, then makes the final 1080x1920 MP4s in output\
cd /d "%~dp0"
python make_shorts.py --template my_settings.json %*
pause
