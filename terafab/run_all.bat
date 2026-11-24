@echo off
REM Full pipeline on the Windows GPU PC. Safe to re-run: finished shots are skipped.
cd /d "%~dp0"
call scripts\check_system.bat
echo.
echo ===== 1/3  5-second motion test (robot wafer handling) =====
python scripts\render_scenes.py --motion-test || (echo Motion test failed - see clips\motion_test. Stopping. & pause & exit /b 1)
echo.
echo ===== 2/3  Rendering 36 shots (resumable; several hours on an 8 GB GPU) =====
python scripts\render_scenes.py %*
echo.
echo ===== 3/3  Editing the movie =====
python scripts\assemble_movie.py
pause
