@echo off
REM Step 2 of the brief: verify GPU, tools, disk and WanGP before rendering. Changes nothing.
setlocal
set WANGP=%USERPROFILE%\WanGP
echo ===== GPU / driver =====
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv || echo !! nvidia-smi failed: install/update NVIDIA driver
echo.
echo ===== Tools =====
where python & python --version
where git & git --version
where ffmpeg & ffmpeg -version | findstr /b "ffmpeg version"
where ffprobe
echo.
echo ===== Free disk (GB) =====
powershell -NoProfile -Command "Get-PSDrive -PSProvider FileSystem | Select-Object Name,@{n='FreeGB';e={[math]::Round($_.Free/1GB,1)}},@{n='UsedGB';e={[math]::Round($_.Used/1GB,1)}} | Format-Table -AutoSize"
echo ===== RAM =====
powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)"
echo.
echo ===== WanGP =====
if exist "%WANGP%\wgp.py" (
  git -C "%WANGP%" log -1 --format="WanGP commit %%h  %%cd"
  echo Python environments:
  for %%E in (env_uv venv .venv env) do if exist "%WANGP%\%%E" echo   %WANGP%\%%E
  echo Downloaded model checkpoints:
  if exist "%WANGP%\ckpts" (dir /b /s "%WANGP%\ckpts\*.safetensors" 2>nul) else echo   none yet - first render downloads Wan2.2 5B weights
) else (
  echo !! WanGP not found at %WANGP%. Run shorts-kit\install_wangp.bat first.
)
pause
