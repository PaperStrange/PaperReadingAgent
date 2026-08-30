# start-agents-dashboard.ps1 - AgentOps 看板一键启动（生产模式，端口 8600，仅回环）
# Windows-only helper（PowerShell）。跨平台等价：
#   cd agents-dashboard; npm run build; npx next start -H 127.0.0.1 -p 8600
# 用法：powershell -ExecutionPolicy Bypass -File .\scripts\start-agents-dashboard.ps1
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Root = Split-Path -Parent $PSScriptRoot
$Dash = Join-Path $Root "agents-dashboard"

# 端口占用预检：8600 被占时给出明确提示，而不是等 next start 报错
$Existing = Get-NetTCPConnection -LocalPort 8600 -State Listen -ErrorAction SilentlyContinue
if ($Existing) {
    Write-Host "==> 端口 8600 已被占用（PID: $($Existing.OwningProcess -join ',')）。请先结束旧看板进程，或手动换端口启动。"
    exit 1
}

if (-not (Test-Path (Join-Path $Dash "node_modules"))) {
    Write-Host "==> 首次运行：安装依赖"
    Push-Location $Dash
    npm ci --no-audit --no-fund
    Pop-Location
}

# 构建（存在 .next 时也重建，保证与源码一致；构建产物不入库）
Write-Host "==> 构建 agents-dashboard（生产模式）"
Push-Location $Dash
npm run build
Pop-Location

$env:AGENT_OPS_DIR = Join-Path $Root "agents"
Write-Host "==> 启动 http://127.0.0.1:8600（仅回环，AGENT_OPS_DIR=$env:AGENT_OPS_DIR）"
Push-Location $Dash
npx next start -H 127.0.0.1 -p 8600
Pop-Location
