# setup-env.ps1 — 一键创建 Windows venv 并安装全部依赖
# 用法：在仓库根目录执行  powershell -ExecutionPolicy Bypass -File .\scripts\setup-env.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "==> 创建 venv: $Root\.venv"
python -m venv "$Root\.venv"

$Py = "$Root\.venv\Scripts\python.exe"
& $Py -m pip install --upgrade pip

# paper-qa 源码包未纳入 git（无 .git 元数据），setuptools-scm 需要伪装版本号
$env:SETUPTOOLS_SCM_PRETEND_VERSION = "2026.1.6.dev10+g36348d0ca"

Write-Host "==> 安装本地 paper-qa 源码包（pypdf[media] + pymupdf readers）"
& $Py -m pip install -e "$Root\paper-qa"
& $Py -m pip install -e "$Root\paper-qa\packages\paper-qa-pypdf[media]"
& $Py -m pip install -e "$Root\paper-qa\packages\paper-qa-pymupdf"

Write-Host "==> 安装其余 Windows 依赖"
& $Py -m pip install -r "$Root\requirements-windows.txt"

Write-Host ""
Write-Host "完成！激活环境："
Write-Host "  .\$Root\.venv\Scripts\Activate.ps1"
