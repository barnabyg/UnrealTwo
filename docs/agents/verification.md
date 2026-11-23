# Verification

## The canonical command

```powershell
Set-Location C:\docs\git\UnrealTwo; pwsh Tools/verify.ps1
```

It needs [uv](https://docs.astral.sh/uv/) and changes no tracked file. GitHub Actions runs the same script on every pull request (`.github/workflows/verify.yml`).

| Gate | Tool | Scope |
|---|---|---|
| Dependencies locked | `uv lock --check` | `pyproject.toml` against `uv.lock` |
| Formatting | `ruff format --check` | all Python in the repo |
| Lint | `ruff check` | all Python in the repo |
| Types | `mypy --strict` | `Tools/mcp`, `Tools/tests` |
| Tests | `pytest` (parallel, warnings are errors) | `Tools/tests` |

## Gates that do not apply

- **Types for `Tools/editor_python`.** Those scripts run inside the editor's interpreter and import `unreal`, which exists only there. They are formatted and linted but not type checked. Review this if Epic publishes type stubs that can be installed outside the editor.
- **Static bug analysis.** Ruff's `B`, `S`, `PL` and `RUF` rule sets cover it for Python; there is no other source language.
- **Vulnerability and package checks.** The tooling has no runtime dependencies. The development tools are pinned in `uv.lock`.
- **Build and packaging.** Beacon is a Blueprint-only project with nothing to compile. Packaging arrives with #18.

## Game content

Blueprints, levels and data assets cannot be checked from a shell. They are verified in the running editor with the verify loop in [verify-loop.md](verify-loop.md): play in editor, drive the game, read the log, capture a screenshot.
