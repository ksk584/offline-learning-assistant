@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Offline Intelligent Learning Assistant (ILA) - Setup and Runner
cd /d "%~dp0"

set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%LOCALAPPDATA%\uv;%PATH%"

echo ===============================================================================
echo   OFFLINE INTELLIGENT LEARNING ASSISTANT (ILA)
echo   On-Device NCERT Class 10 Master Notes and Live Lecture Transcription
echo   SDG 4 - Fully Offline Architecture - Zero Cloud Dependency
echo ===============================================================================
echo.

:: -------------------------------------------------------------------------
:: 1. Detect Python
:: -------------------------------------------------------------------------
echo [*] Checking Python installation...
set "PYTHON_CMD="

python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
    goto :python_found
)

py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py -3"
    goto :python_found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :python_found
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :python_found
)

if exist "%ProgramFiles%\Python312\python.exe" (
    set "PYTHON_CMD=%ProgramFiles%\Python312\python.exe"
    goto :python_found
)

if exist "%ProgramFiles%\Python311\python.exe" (
    set "PYTHON_CMD=%ProgramFiles%\Python311\python.exe"
    goto :python_found
)

echo [!] ERROR: Python 3.11 or 3.12 was not found on your system!
echo Please install Python 3.11+ from https://www.python.org/downloads/
echo IMPORTANT: Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:python_found
for /f "tokens=*" %%v in ('!PYTHON_CMD! --version 2^>^&1') do set "PY_VER=%%v"
echo [✓] Found !PY_VER! (!PYTHON_CMD!)

:: -------------------------------------------------------------------------
:: 2. Check / Install uv (Ultra-Fast Package Manager)
:: -------------------------------------------------------------------------
echo [*] Checking package manager (uv)...
set "UV_CMD="

uv --version >nul 2>&1
if !errorlevel! equ 0 (
    set "UV_CMD=uv"
    goto :uv_found
)

if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
    goto :uv_found
)

if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
    set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"
    goto :uv_found
)

if exist "%LOCALAPPDATA%\uv\uv.exe" (
    set "UV_CMD=%LOCALAPPDATA%\uv\uv.exe"
    goto :uv_found
)

if exist ".venv\Scripts\uv.exe" (
    set "UV_CMD=.venv\Scripts\uv.exe"
    goto :uv_found
)

echo [*] Installing uv for high-speed offline environment management...
!PYTHON_CMD! -m pip install --upgrade uv >nul 2>&1
if !errorlevel! equ 0 (
    set "UV_CMD=!PYTHON_CMD! -m uv"
    goto :uv_found
)

:: Fallback install via powershell script
powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
    goto :uv_found
)
if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
    set "UV_CMD=%USERPROFILE%\.cargo\bin\uv.exe"
    goto :uv_found
)

echo [!] Could not auto-install uv; falling back to standard pip.

:uv_found
if defined UV_CMD (
    echo [✓] Package manager ready.
)

:: -------------------------------------------------------------------------
:: 3. Setup Virtual Environment and Install Dependencies
:: -------------------------------------------------------------------------
echo [*] Setting up Python virtual environment and dependencies...

if defined UV_CMD (
    "!UV_CMD!" sync --extra llm
    if !errorlevel! neq 0 (
        echo [*] Running fallback dependency install with pre-compiled wheels...
        "!UV_CMD!" venv .venv
        "!UV_CMD!" pip install -e .[llm] --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
        if !errorlevel! neq 0 (
            echo [*] Installing core package dependencies...
            "!UV_CMD!" pip install -e .
        )
    )
) else (
    if not exist ".venv\Scripts\activate.bat" (
        !PYTHON_CMD! -m venv .venv
    )
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -e .[llm] --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
    if !errorlevel! neq 0 (
        pip install -e .
    )
)

echo [✓] Core dependencies and virtual environment ready.

:: -------------------------------------------------------------------------
:: 4. Verify / Auto-Download Local LLM Note-Writing Model
:: -------------------------------------------------------------------------
echo [*] Checking on-device LLM model...
set "MODEL_FOUND=0"

if exist models\llm\*.gguf set "MODEL_FOUND=1"
if exist %USERPROFILE%\.ila\models\llm\*.gguf set "MODEL_FOUND=1"

if "!MODEL_FOUND!"=="1" goto :model_ready

echo [!] No offline LLM model detected.
echo [*] Downloading local Qwen 3.5 model - 532 MB - from Hugging Face for 100%% offline notes...
if not exist "models\llm" mkdir "models\llm"
if defined UV_CMD (
    "!UV_CMD!" run ila download-llm --profile potato
) else (
    .venv\Scripts\python -m ila.cli download-llm --profile potato
)
if !errorlevel! equ 0 (
    echo [✓] Model downloaded and verified successfully!
) else (
    echo [!] Note: LLM download can be resumed anytime via: ila download-llm
)
goto :model_done

:model_ready
echo [✓] Offline LLM model found and verified.

:model_done

:: -------------------------------------------------------------------------
:: 5. Verify Frontend Web Application
:: -------------------------------------------------------------------------
echo [*] Verifying Web Dashboard...
if not exist "dashboard\dist\index.html" (
    echo [!] Pre-compiled dashboard not found. Checking Node.js/npm to build...
    where npm >nul 2>&1
    if !errorlevel! equ 0 (
        echo [*] Building React dashboard...
        cd dashboard && npm install && npm run build && cd ..
    ) else (
        echo [!] Warning: Node.js/npm not found to build dashboard.
    )
) else (
    echo [✓] Dashboard is compiled and ready to serve.
)

:: -------------------------------------------------------------------------
:: 6. Launch Application Server and Open Browser
:: -------------------------------------------------------------------------
echo.
echo ===============================================================================
echo   ILA IS READY! STARTING LOCAL SERVER...
echo   Url: http://127.0.0.1:8765
echo.
echo   Features:
echo   - NCERT Class 10 Units 1, 2, 3 Master Notes (10-Page Comprehensive Guides)
echo   - Real-time on-device speech transcription (Faster-Whisper)
echo   - Local notes synthesis and grounding verification (Qwen 3.5 GGUF)
echo.
echo   Press Ctrl+C in this terminal window to stop the server.
echo ===============================================================================
echo.

:: Start background watcher that waits until 127.0.0.1:8765 is actively listening before opening browser
start "" powershell -NoProfile -WindowStyle Hidden -Command "$done=$false; for($i=0;$i -lt 40;$i++){ Start-Sleep -Milliseconds 500; try { $t=New-Object Net.Sockets.TcpClient; $t.Connect('127.0.0.1', 8765); $t.Close(); $done=$true; break } catch{} }; if($done){ Start-Process 'http://127.0.0.1:8765' }"

:: Start the application
if defined UV_CMD (
    "!UV_CMD!" run ila serve --host 127.0.0.1 --port 8765 --open
) else (
    .venv\Scripts\ila.exe serve --host 127.0.0.1 --port 8765 --open
)

pause
