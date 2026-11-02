<#
.SYNOPSIS
  Study 2's model matrix (T-22): 11 tasks x A on Opus, A on Haiku, B-hs and B-so x 3 runs = 132 runs.

.DESCRIPTION
  Runs one phase at a time, one process per task within a phase, started 15 seconds apart because sweep ids
  have one-second resolution. Each process pauses at a usage limit and resumes (see run_sweep.ps1). Opus goes
  first so its effect on the usage bars shows early. Caps are API-equivalent dollars, not a charge: $2 per run,
  and $20 per task split across the phases.
#>
param([switch]$DryRun)

$here = $PSScriptRoot
$tasks = "t22","t25","t34","t37","t38","t39","t40","t42","t43","t44","t45"
$phases = @(
    @{ Configs = "A";         Model = "opus";  TaskCap = 5 },
    @{ Configs = "A";         Model = "haiku"; TaskCap = 4 },
    @{ Configs = "B-hs,B-so"; Model = "";      TaskCap = 11 }
)

foreach ($ph in $phases) {
    Write-Host "phase start: $($ph.Configs) $($ph.Model) at $(Get-Date -Format s)"
    $procs = foreach ($t in $tasks) {
        $argv = @("-NoProfile", "-File", "$here\run_sweep.ps1", "-Tasks", $t, "-Configs", "`"$($ph.Configs)`"", "-Reps", "3",
                  "-RunCap", "2", "-TotalCap", "$($ph.TaskCap)")
        if ($ph.Model) { $argv += @("-Model", $ph.Model) }
        if ($DryRun) { $argv += "-DryRun" }
        Start-Process powershell -ArgumentList $argv -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 15
    }
    $procs | Wait-Process
    Write-Host "phase done: $($ph.Configs) $($ph.Model) at $(Get-Date -Format s)"
}
Write-Host "matrix finished at $(Get-Date -Format s)"
