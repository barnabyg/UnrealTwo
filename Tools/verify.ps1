#!/usr/bin/env pwsh
# Canonical, non-mutating verification: the Python tooling and the C++ formatting everywhere,
# and the C++ build and tests where Unreal Engine is installed.
# Usage (repo root): pwsh Tools/verify.ps1
# Gates that do not apply are listed in docs/agents/verification.md.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Gate([string]$Name, [scriptblock]$Command) {
    Write-Host "== $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Name failed" }
}

Invoke-Gate 'dependencies locked' { uv lock --check }
Invoke-Gate 'install' { uv sync --locked --group dev --quiet }
Invoke-Gate 'format' { uv run --no-sync ruff format --check . }
Invoke-Gate 'lint' { uv run --no-sync ruff check . }
Invoke-Gate 'types' { uv run --no-sync mypy }
# CI stops at the first failing test; a local run reports them all. The array is typed
# because an `if` expression unwraps a one-element array to a string, and splatting a
# string passes it one character at a time.
[string[]]$failFast = @()
if ($env:CI) { $failFast = @('--maxfail=1') }
Invoke-Gate 'tests' { uv run --no-sync pytest @failFast }
# clang-format comes from uv.lock, so every machine formats with the same version.
$cppSources = @(Get-ChildItem Source -Recurse -File -Include *.cpp, *.h, *.cs | ForEach-Object FullName)
Invoke-Gate 'format (C++)' { uv run --no-sync clang-format --dry-run --Werror @cppSources }

# The other C++ gates need the engine and its compiler, which a hosted CI runner does not have.
$engine = if ($env:UE_ROOT) { $env:UE_ROOT } else { 'C:/Program Files/Epic Games/UE_5.8' }
# The path is put together as text: on Linux, Join-Path stops on a path whose drive does not exist.
if (Test-Path -LiteralPath "$engine/Engine/Build/BatchFiles/Build.bat") {
    & (Join-Path $PSScriptRoot 'verify-cpp.ps1') -Engine $engine
    Write-Host 'verify: all gates passed'
}
else {
    Write-Host "== C++ build and tests skipped: no Unreal Engine at $engine (see docs/agents/verification.md)"
    Write-Host 'verify: the gates that ran passed; the C++ build and tests did not run'
}
