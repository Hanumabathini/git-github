@echo off
REM ============================================================
REM  Installs WanGP (Wan2GP) + ffmpeg on Windows with an NVIDIA GPU.
REM  Run by double-clicking. Needs internet. Takes 20-60 minutes.
REM ============================================================
setlocal
set KIT=%~dp0
set WANGP=%USERPROFILE%\WanGP

echo [1/4] Checking NVIDIA GPU...
nvidia-smi >nul 2>&1 || (echo No NVIDIA GPU/driver found. Install the latest NVIDIA driver first. & pause & exit /b 1)
nvidia-smi --query-gpu=name,memory.total --format=csv

echo [2/4] Installing Git, Python 3.11 and ffmpeg with winget (skips what you already have)...
winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements

echo [3/4] Downloading WanGP to %WANGP% ...
if not exist "%WANGP%\wgp.py" (
  git clone https://github.com/deepbeepmeep/Wan2GP.git "%WANGP%" || (echo Open a NEW terminal so git is on PATH, then run this again. & pause & exit /b 1)
) else (
  git -C "%WANGP%" pull
)

echo [4/4] Starting WanGP's official installer. Choose "Auto Install" when asked.
call "%WANGP%\scripts\install.bat"

echo.
echo Done. Next: double-click start_wangp.bat
pause
