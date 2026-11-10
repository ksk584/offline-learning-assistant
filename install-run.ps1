<#
.SYNOPSIS
    Singular setup and runner for Offline Intelligent Learning Assistant (ILA).
    Works on any Windows device with Python 3.11+.
#>

$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "  OFFLINE INTELLIGENT LEARNING ASSISTANT (ILA)" -ForegroundColor Cyan
Write-Host "  On-Device NCERT Class 10 Master Notes & Live Lecture Transcription" -ForegroundColor Cyan
Write-Host "  SDG 4 · Fully Offline Architecture · Zero Cloud Dependency" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Detect Python
Write-Host "[*] Checking Python installation..." -ForegroundColor Yellow
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py -3"
} else {
    $CommonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    foreach ($p in $CommonPaths) {
        if (Test-Path $p) {
            $PythonCmd = $p
            break
        }
    }
}

if (-not $PythonCmd) {
    Write-Host "[!] ERROR: Python 3.11+ was not found on your system!" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/ (check 'Add Python to PATH')" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$PyVer = & $PythonCmd --version 2>&1
Write-Host "[✓] Found $PyVer ($PythonCmd)" -ForegroundColor Green

# 2. Check / Install uv
Write-Host "[*] Checking package manager (uv)..." -ForegroundColor Yellow
$UvCmd = $null
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $UvCmd = "uv"
} elseif (Test-Path "$env:USERPROFILE\.cargo\bin\uv.exe") {
    $UvCmd = "$env:USERPROFILE\.cargo\bin\uv.exe"
} elseif (Test-Path "$env:LOCALAPPDATA\uv\uv.exe") {
    $UvCmd = "$env:LOCALAPPDATA\uv\uv.exe"
} else {
    Write-Host "[*] Installing uv for fast dependency management..." -ForegroundColor Yellow
    & $PythonCmd -m pip install --upgrade uv 2>$null
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $UvCmd = "uv"
    }
}

if ($UvCmd) {
    Write-Host "[✓] Package manager ($UvCmd) ready." -ForegroundColor Green
}

# 3. Setup Dependencies
Write-Host "[*] Syncing virtual environment and dependencies..." -ForegroundColor Yellow
if ($UvCmd) {
    & $UvCmd sync --extra llm
} else {
    if (-not (Test-Path ".venv\Scripts\activate.ps1")) {
        & $PythonCmd -m venv .venv
    }
    & ".venv\Scripts\python.exe" -m pip install -e ".[llm]" pypdf huggingface-hub
}
Write-Host "[✓] Dependencies installed." -ForegroundColor Green

# 4. Check Local LLM Models
Write-Host "[*] Checking on-device LLM model..." -ForegroundColor Yellow
$ModelExists = $false
$ModelCandidates = @(
    "models\llm\Qwen3.5-0.8B-Q4_K_M.gguf",
    "models\llm\Qwen3.5-2B-Q4_K_M.gguf",
    "$env:USERPROFILE\.ila\models\llm\Qwen3.5-0.8B-Q4_K_M.gguf",
    "$env:USERPROFILE\.ila\models\llm\Qwen3.5-2B-Q4_K_M.gguf"
)
foreach ($m in $ModelCandidates) {
    if (Test-Path $m) {
        $ModelExists = $true
        break
    }
}

if ($ModelExists) {
    Write-Host "[✓] Offline LLM model found." -ForegroundColor Green
} else {
    Write-Host "[!] No offline LLM model detected." -ForegroundColor Yellow
    Write-Host "[*] Downloading local Qwen 3.5 model (~532 MB) from Hugging Face..." -ForegroundColor Yellow
    if ($UvCmd) {
        & $UvCmd run ila download-llm --profile potato
    } else {
        & ".venv\Scripts\python.exe" -m ila.cli download-llm --profile potato
    }
    Write-Host "[✓] Model ready." -ForegroundColor Green
}

# 5. Check Dashboard
Write-Host "[*] Verifying Web Dashboard..." -ForegroundColor Yellow
if (Test-Path "dashboard\dist\index.html") {
    Write-Host "[✓] Dashboard is compiled and ready." -ForegroundColor Green
} else {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "[*] Building React dashboard..." -ForegroundColor Yellow
        Push-Location dashboard
        npm install
        npm run build
        Pop-Location
    }
}

# 6. Launch Server & Open Browser
Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "  ILA SERVER STARTING: http://127.0.0.1:8765" -ForegroundColor Green
Write-Host "  Press Ctrl+C in this terminal window to stop the server." -ForegroundColor Yellow
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:8765"
} | Out-Null

if ($UvCmd) {
    & $UvCmd run ila serve --host 127.0.0.1 --port 8765
} else {
    & ".venv\Scripts\ila.exe" serve --host 127.0.0.1 --port 8765
}
