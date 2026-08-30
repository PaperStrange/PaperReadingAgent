# start-agents-dashboard.ps1 - AgentOps 看板一键启动（生产模式，端口 8600）
# 用法：powershell -ExecutionPolicy Bypass -File .\scripts\start-agents-dashboard.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Dash = Join-Path $Root "agents-dashboard"

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
Write-Host "==> 启动 http://127.0.0.1:8600（AGENT_OPS_DIR=$env:AGENT_OPS_DIR）"
Push-Location $Dash
npx next start -p 8600
Pop-Location
