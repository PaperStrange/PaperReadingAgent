# start-streamlit.ps1 — 启动 Streamlit 调试 UI（默认 http://127.0.0.1:8501）
# 用法：powershell -ExecutionPolicy Bypass -File .\scripts\start-streamlit.ps1
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

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
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"

& "$Root\.venv\Scripts\python.exe" -m streamlit run "$Root\paper-qa-script\streamlit_paperqa_app.py"
