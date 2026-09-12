# register-scheduled-tasks.ps1 - TG-5 scheduled-task registration helper (Windows Task Scheduler).
#
# WHY: the local desktop app is not always running, so an in-process timer would silently miss runs.
# This helper registers a weekly Windows task that calls the cross-platform entry point
# (scripts/scheduled-tasks.py --check-due), which decides from agents/runtime/schedule.json whether
# the run is actually due - missed runs are caught up once on the next fire, never silently dropped
# and never replayed in a burst.
#
# NOTE: keep this file pure ASCII (PS 5.1 reads BOM-less UTF-8 .ps1 as ANSI; Chinese comments can
# swallow line breaks and break parsing - 3-LEARNED 1.18 sibling issue).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\register-scheduled-tasks.ps1 -Action register
#   powershell -ExecutionPolicy Bypass -File .\scripts\register-scheduled-tasks.ps1 -Action register -Task nightly-suite -DayOfWeek Sunday -At 03:30
#   powershell -ExecutionPolicy Bypass -File .\scripts\register-scheduled-tasks.ps1 -Action unregister
#   powershell -ExecutionPolicy Bypass -File .\scripts\register-scheduled-tasks.ps1 -Action status
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("register", "unregister", "status")]
    [string]$Action,

    [ValidateSet("nightly-suite", "prices", "providers")]
    [string]$Task = "nightly-suite",

    [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
    [string]$DayOfWeek = "Sunday",

    [string]$At = "03:30"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Entry = Join-Path $RepoRoot "scripts\scheduled-tasks.py"
$TaskName = "PaperReading-$Task"

if (-not (Test-Path $Py)) { throw "venv python not found: $Py (run scripts/setup-env.ps1 first)" }
if (-not (Test-Path $Entry)) { throw "entry point not found: $Entry" }

switch ($Action) {
    "register" {
        $action = New-ScheduledTaskAction -Execute $Py -Argument "`"$Entry`" --task $Task --check-due" -WorkingDirectory $RepoRoot
        $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $At
        # StartWhenAvailable: catch up a missed fire instead of skipping it silently
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 3)
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "PaperReading $Task (due check via scheduled-tasks.py; budget gate applies)" -Force | Out-Null
        Write-Output "REGISTERED: $TaskName (weekly $DayOfWeek $At, StartWhenAvailable=true)"
        Write-Output "  run now:    powershell -File .\scripts\register-scheduled-tasks.ps1 -Action status"
        Write-Output "  unregister: powershell -File .\scripts\register-scheduled-tasks.ps1 -Action unregister -Task $Task"
    }
    "unregister" {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "UNREGISTERED: $TaskName"
    }
    "status" {
        $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if (-not $t) { Write-Output "NOT REGISTERED: $TaskName"; exit 0 }
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Output "TASK: $TaskName"
        Write-Output "  state:        $($t.State)"
        Write-Output "  last run:     $($info.LastRunTime)  result=$($info.LastTaskResult)"
        Write-Output "  next run:     $($info.NextRunTime)"
    }
}
