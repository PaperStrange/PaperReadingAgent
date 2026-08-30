# start-agents-dashboard.ps1 - AgentOps dashboard one-click start (production mode, port 8600, loopback only)
# Windows-only helper (PowerShell). Cross-platform equivalent:
#   cd agents-dashboard; npm run build; npx next start -H 127.0.0.1 -p 8600
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\start-agents-dashboard.ps1
# NOTE: keep this file pure ASCII (PS 5.1 reads BOM-less UTF-8 .ps1 as ANSI - see 3-LEARNED 1.18).
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
$Dash = Join-Path $Root "agents-dashboard"

# Port precheck: friendly message when 8600 is taken, instead of a raw next start error
$Existing = Get-NetTCPConnection -LocalPort 8600 -State Listen -ErrorAction SilentlyContinue
if ($Existing) {
    Write-Host "==> port 8600 is in use (PID: $($Existing.OwningProcess -join ',')). Stop the old dashboard first, or start manually on another port."
    exit 1
}

if (-not (Test-Path (Join-Path $Dash "node_modules"))) {
    Write-Host "==> first run: installing dependencies"
    Push-Location $Dash
    npm ci --no-audit --no-fund
    Pop-Location
}

# Rebuild even when .next exists (keep build in sync with sources; build output is not committed)
Write-Host "==> building agents-dashboard (production)"
Push-Location $Dash
npm run build
Pop-Location

$env:AGENT_OPS_DIR = Join-Path $Root "agents"
Write-Host "==> starting http://127.0.0.1:8600 (loopback only; AGENT_OPS_DIR=$env:AGENT_OPS_DIR)"
Push-Location $Dash
npx next start -H 127.0.0.1 -p 8600
Pop-Location
