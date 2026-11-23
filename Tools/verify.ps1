#!/usr/bin/env pwsh
# Canonical, non-mutating verification for the repo's Python tooling.
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
$bail = if ($env:CI) { @('--maxfail=1') } else { @() }
Invoke-Gate 'tests' { uv run --no-sync pytest @bail }
Write-Host 'verify: all gates passed'
