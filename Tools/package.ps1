#!/usr/bin/env pwsh
# Packages Beacon as a standalone Windows build: builds the game target, cooks the content,
# stages it into .pak files and archives the result to Packaged/Windows (Git ignores Packaged/).
# Usage (repo root): pwsh Tools/package.ps1 [-Configuration Development|Shipping] [-Engine <root>]
# The MCP has no build or packaging tool, so this runs the engine's own RunUAT BuildCookRun.
# It works with the editor open: it does not rebuild the editor's modules, and the cook runs
# in a separate, windowless editor process. See docs/agents/packaging.md.
param(
    [ValidateSet('Development', 'Shipping')][string]$Configuration = 'Development',
    [string]$Engine = $(if ($env:UE_ROOT) { $env:UE_ROOT } else { 'C:/Program Files/Epic Games/UE_5.8' })
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$runUat = "$Engine/Engine/Build/BatchFiles/RunUAT.bat"
if (-not (Test-Path -LiteralPath $runUat)) { throw "package: no Unreal Engine at $Engine (set UE_ROOT)" }

$project = Join-Path $repo 'Beacon.uproject'
$archive = Join-Path $repo 'Packaged'
$logs = Join-Path $repo 'Saved/Logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$log = Join-Path $logs 'package.log'

# Packaging takes minutes and every core, so it runs below normal priority to keep the PC
# responsive. Child processes (the compiler, the cook, shader workers) inherit the class.
# The caller's priority is put back afterwards, in case the script was run with & or dot-sourced.
$shell = Get-Process -Id $PID
$priority = $shell.PriorityClass
$shell.PriorityClass = 'BelowNormal'

# Paths are quoted so that a repository or engine path with a space survives cmd.exe.
$uatArguments = @(
    'BuildCookRun', "-project=`"$project`"", '-target=Beacon', '-platform=Win64',
    "-clientconfig=$Configuration", '-build', '-cook', '-stage', '-pak', '-iostore',
    '-archive', "-archivedirectory=`"$archive`"",
    # The editor may be open, and it holds its own modules' DLLs; only the game is built.
    '-nocompileeditor', '-skipbuildeditor', '-nop4', '-utf8output', '-unattended'
) -join ' '
Write-Host "== package ($Configuration): output in $log"
$started = Get-Date
try {
    $uat = Start-Process $runUat -ArgumentList $uatArguments -NoNewWindow -PassThru `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err"
    $null = $uat.Handle # keeps the exit code readable after the process ends
    # A first build takes about three minutes; 30 minutes means it has hung.
    if (-not $uat.WaitForExit(1800000)) {
        $uat.Kill($true)
        throw "package failed: UAT did not finish within 30 minutes: see $log"
    }
    $exitCode = $uat.ExitCode
}
finally {
    $shell.PriorityClass = $priority
}
$minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
if ($exitCode -ne 0) {
    Get-Content $log, "$log.err" -Tail 40 | Write-Host
    throw "package failed after $minutes min with exit code ${exitCode}: see $log"
}
$exe = Join-Path $archive 'Windows/Beacon.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "package: UAT succeeded but $exe is missing: see $log" }
Write-Host "package: built in $minutes min. Run $exe"
