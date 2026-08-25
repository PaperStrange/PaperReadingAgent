# start-frontend.ps1 — 启动 ReactFlow 前端开发服务器（Vite，http://127.0.0.1:5173）
# 用法：powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "paper-qa-script\reactflow-paperqa-prototype\frontend"

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "==> 首次运行：npm ci"
    Push-Location $Frontend
    npm ci
    Pop-Location
}

Set-Location $Frontend
# 直接调用 vite（npm run dev -- 传参在 Windows 上不可靠；--host 显式绑定 IPv4）
& "$Frontend\node_modules\.bin\vite.cmd" --host 127.0.0.1 --port 5173 --strictPort
