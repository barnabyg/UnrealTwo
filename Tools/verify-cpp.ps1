#!/usr/bin/env pwsh
# The C++ gates of Tools/verify.ps1 that need Unreal Engine 5.8 and Visual Studio: the build
# and the tests of the modules under Source/. verify.ps1 runs them only where the engine is
# installed. Usage (repo root): pwsh Tools/verify-cpp.ps1 -Engine <engine root>
param([Parameter(Mandatory)][string]$Engine)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$project = Join-Path $repo 'Beacon.uproject'
$logs = Join-Path $repo 'Saved/Logs'
New-Item -ItemType Directory -Force $logs | Out-Null

# Runs Unreal Build Tool on the editor target with its output sent to a file. Any warning in
# it fails the gate, apart from the two that docs/agents/verification.md documents: C4996
# raised inside the engine's own headers, and the notice that the compiler is newer than
# the engine prefers.
function Invoke-BuildGate([string]$Name, [string]$LogName) {
    Write-Host "== $Name"
    $log = Join-Path $logs $LogName
    & (Join-Path $Engine 'Engine/Build/BatchFiles/Build.bat') BeaconEditor Win64 Development `
        "-Project=$project" -WaitMutex -NoHotReloadFromIDE *> $log
    if ($LASTEXITCODE -ne 0) {
        Get-Content $log -Tail 40 | Write-Host
        throw "$Name failed: see $log. The editor must be closed when there is something to compile."
    }
    $engineHeader = '^' + [regex]::Escape((Resolve-Path $Engine).Path) + '.*: warning C4996:'
    $warnings = @(Select-String -Path $log -Pattern '\bwarning\b' | ForEach-Object Line |
            Where-Object { $_ -notmatch $engineHeader -and $_ -notmatch 'is not a preferred version' })
    if ($warnings) {
        $warnings | Write-Host
        throw "$Name failed: $($warnings.Count) warning(s)"
    }
    if (Select-String -Path $log -SimpleMatch -Pattern 'Target is up to date' -Quiet) {
        # Warnings are printed when a file is compiled, so an up-to-date target shows none either way.
        Write-Host 'up to date: nothing was compiled'
    }
}

Invoke-BuildGate 'build (C++)' 'verify-build.log'

# A second, windowless editor runs the tests, so this works while the editor is open.
# It gets its own MCP port because the open editor holds the usual one.
Write-Host '== tests (C++)'
$report = Join-Path $repo 'Saved/Automation/verify'
if (Test-Path $report) { Remove-Item -Recurse -Force $report }
$editorArguments = @(
    "`"$project`"",
    '-ExecCmds="Automation RunTests StartsWith:Beacon.; Quit"',
    '-unattended', '-nopause', '-nosplash', '-nullrhi', '-nosound',
    '-ModelContextProtocolPort=8017',
    "-ReportExportPath=`"$report`"",
    "-abslog=`"$(Join-Path $logs 'verify-tests.log')`""
)
$editor = Start-Process (Join-Path $Engine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') `
    -ArgumentList $editorArguments -PassThru -WindowStyle Hidden
# Ten minutes is several times what a start-up and the tests take.
if (-not $editor.WaitForExit(600000)) {
    $editor.Kill($true)
    throw 'tests (C++) failed: the editor did not finish within ten minutes'
}
$index = Join-Path $report 'index.json'
if (-not (Test-Path $index)) { throw "tests (C++) failed: no report was written. See $logs/verify-tests.log" }
$results = Get-Content $index -Raw | ConvertFrom-Json
$notClean = $results.tests | Where-Object { $_.state -ne 'Success' -or $_.warnings -ne 0 -or $_.errors -ne 0 }
$notClean | ForEach-Object { Write-Host "$($_.state): $($_.fullTestPath)" }
if ($results.succeeded -eq 0 -or $notClean -or $results.notRun -ne 0) {
    throw "tests (C++) failed: $($results.failed) failed, $($results.succeededWithWarnings) passed with warnings, $($results.notRun) not run"
}
Write-Host "$($results.succeeded) passed"
