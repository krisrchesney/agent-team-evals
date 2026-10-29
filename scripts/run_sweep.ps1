<#
.SYNOPSIS
  Run an ate sweep unattended, and carry on after a usage-limit stop.

.DESCRIPTION
  Calls `python -m ate run ...`. If the sweep stops because the plan's usage limit was reached, it waits
  and resumes the same sweep (finished runs are skipped, rate-limited ones are re-run). It stops for good
  when the sweep finishes, when anything else halts it (a leak or auth check, the sweep cap), or after
  -MaxHours. Everything it prints is also appended to results\sweep-<time>.log.

  Real runs use your Claude subscription (plan usage, nothing billed). Turn "extra usage" off in claude.ai
  first, and run `python -m ate auth` once. -DryRun uses the fake CLI and uses no plan usage.

.EXAMPLE
  powershell -File scripts\run_sweep.ps1 -DryRun
  powershell -File scripts\run_sweep.ps1 -Tasks "t01,t02,t03,t04,t05" -Reps 3
#>
param(
    [string]$Tasks = "all",
    [string]$Configs = "A,B,C",
    [int]$Reps = 3,
    [double]$RunCap = 1.5,        # runaway-loop cap per run, API-equivalent dollars (not a spending limit)
    [double]$TotalCap = 15,       # runaway-loop cap for the whole sweep, API-equivalent dollars
    [int]$MaxHours = 8,
    [int]$WaitMinutes = 30,
    [switch]$DryRun
)

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$log = Join-Path $repo "results\sweep-$stamp.log"
New-Item -ItemType Directory -Force (Join-Path $repo "results") | Out-Null
$deadline = (Get-Date).AddHours($MaxHours)
$resume = $null

while ($true) {
    $argv = @("-m", "ate", "run", "--tasks", $Tasks, "--configs", $Configs, "--reps", $Reps,
              "--run-cap", $RunCap, "--max-total-api-equiv", $TotalCap)
    if ($DryRun) { $argv += @("--dry-run", "--oracle") } else { $argv += "--yes" }
    if ($resume) { $argv += @("--resume", $resume) }

    $lines = & python @argv | Tee-Object -FilePath $log -Append | ForEach-Object { Write-Host $_; $_ }
    $code = $LASTEXITCODE
    $text = ($lines | Out-String)

    if ($code -eq 0) { Write-Host "sweep finished"; break }
    if ($code -ne 3 -or $text -notmatch "usage limit reached") {
        Write-Host "stopped (exit $code); not a usage limit, so not retrying. See the lines above."
        break
    }
    if ($text -match "results: .*[\\/]([^\\/]+)\.jsonl") { $resume = $Matches[1] }
    if (-not $resume) { Write-Host "usage limit hit but no sweep id found; stopping"; break }
    if ((Get-Date).AddMinutes($WaitMinutes) -gt $deadline) {
        Write-Host "usage limit hit and -MaxHours reached; resume later with: --resume $resume"
        break
    }
    Write-Host "usage limit reached; waiting $WaitMinutes min, then resuming $resume"
    Start-Sleep -Seconds ($WaitMinutes * 60)
}
if ($code -ne $null) { exit $code }
