# start-backend.ps1 — 启动 FastAPI 后端（http://127.0.0.1:8787）
# 用法：powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# 读取 paper-qa-script\.env（bash 风格 export KEY=value），导入环境变量
$envFile = Join-Path $Root "paper-qa-script\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*export\s+([^=]+)=(.*)$') {
            Set-Item -Path "Env:$($matches[1])" -Value $matches[2].Trim()
        } elseif ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            Set-Item -Path "Env:$($matches[1])" -Value $matches[2].Trim()
        }
    }
}

# 关闭 huggingface symlink 警告（Windows 无 symlink 权限时仅影响缓存提示）
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

Write-Host "开始后端：$Root\paper-qa-script\reactflow-paperqa-prototype\backend\main.py"
& "$Root\.venv\Scripts\python.exe" "$Root\paper-qa-script\reactflow-paperqa-prototype\backend\main.py"
