# github-pr.ps1 - UTF-8-safe GitHub PR create/patch/merge/get helper (REST API).
#
# Background (3-LEARNED lesson 1.18): PowerShell 5.1 encodes string -Body as ANSI
# (GBK on Chinese Windows), GitHub decodes as UTF-8 -> mojibake in PR titles/bodies.
# This script sends the JSON as UTF-8 BYTES with charset=utf-8, which is mojibake-proof.
#
# NOTE: keep this file pure ASCII (PS 5.1 reads BOM-less UTF-8 .ps1 as ANSI,
# and Chinese comments can swallow line breaks and break parsing).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\github-pr.ps1 create -Base main -Head sync/xxx -Title "Title" -Body "Body"
#   powershell -ExecutionPolicy Bypass -File .\scripts\github-pr.ps1 patch -Number 2 -Title "New" -Body "New body"
#   powershell -ExecutionPolicy Bypass -File .\scripts\github-pr.ps1 merge -Number 3 -Method merge
#   powershell -ExecutionPolicy Bypass -File .\scripts\github-pr.ps1 get -Number 2
#
# Credentials: reuses the GitHub credential stored in git credential manager.
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("create", "patch", "merge", "get")]
    [string]$Action,

    [string]$Base = "main",
    [string]$Head = "",
    [int]$Number = 0,
    [string]$Title = "",
    [string]$Body = "",
    [string]$Method = "merge"
)

$ErrorActionPreference = "Stop"
$Repo = "PaperStrange/PaperReadingAgent"
$Api = "https://api.github.com/repos/$Repo"

# 1) read token from git credential (never printed)
$cred = (echo "protocol=https`nhost=github.com`n" | git credential fill) -split "`n"
$token = ($cred | Where-Object { $_ -match "^password=" }) -replace "^password=", ""
if (-not $token) { throw "cannot read GitHub credential from git" }

$headers = @{
    Authorization = "Bearer $token"
    "User-Agent" = "dsh-sync"
    Accept        = "application/vnd.github+json"
}

function Invoke-GitHubJson {
    param([string]$Uri, [string]$HttpMethod, [hashtable]$Payload)
    if ($Payload) {
        $json = $Payload | ConvertTo-Json -Compress -Depth 8
        # UTF-8 byte body: the only reliable way for non-ASCII content under PS 5.1
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
        return Invoke-RestMethod -Method $HttpMethod -Uri $Uri -Headers $headers -ContentType "application/json; charset=utf-8" -Body $bytes
    }
    return Invoke-RestMethod -Method $HttpMethod -Uri $Uri -Headers $headers
}

switch ($Action) {
    "get" {
        if ($Number -le 0) { throw "get requires -Number" }
        $pr = Invoke-GitHubJson -Uri "$Api/pulls/$Number" -HttpMethod "Get"
        Write-Output ("title: {0}" -f $pr.title)
        Write-Output ("state: {0}" -f $pr.state)
        Write-Output ("body:`n{0}" -f $pr.body)
    }
    "create" {
        if (-not $Head -or -not $Title) { throw "create requires -Head and -Title" }
        $payload = [ordered]@{ title = $Title; head = $Head; base = $Base; body = $Body }
        $pr = Invoke-GitHubJson -Uri "$Api/pulls" -HttpMethod "Post" -Payload $payload
        Write-Output ("PR #{0}: {1}" -f $pr.number, $pr.html_url)
    }
    "patch" {
        if ($Number -le 0) { throw "patch requires -Number" }
        $payload = [ordered]@{}
        if ($Title) { $payload.title = $Title }
        if ($Body) { $payload.body = $Body }
        $pr = Invoke-GitHubJson -Uri "$Api/pulls/$Number" -HttpMethod "Patch" -Payload $payload
        Write-Output ("PATCH #{0} OK, updated_at={1}" -f $pr.number, $pr.updated_at)
    }
    "merge" {
        if ($Number -le 0) { throw "merge requires -Number" }
        if (-not $Head) {
            # fetch the PR to build a complete merge commit title
            $prInfo = Invoke-GitHubJson -Uri "$Api/pulls/$Number" -HttpMethod "Get"
            $Head = ($prInfo.head.label -replace ":", "/")
        }
        $payload = [ordered]@{ merge_method = $Method; commit_title = "Merge pull request #$Number from $Head" }
        $m = Invoke-GitHubJson -Uri "$Api/pulls/$Number/merge" -HttpMethod "Put" -Payload $payload
        Write-Output ("MERGED #{0}: {1}" -f $Number, $m.sha)
    }
}
