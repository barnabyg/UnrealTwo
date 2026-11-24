# Verification

## The canonical command

```powershell
Set-Location C:\docs\git\UnrealTwo; pwsh Tools/verify.ps1
```

It needs [uv](https://docs.astral.sh/uv/) and changes no tracked file. GitHub Actions runs the same script on every pull request (`.github/workflows/verify.yml`).

| Gate | Tool | Scope | Runs in CI |
|---|---|---|---|
| Dependencies locked | `uv lock --check` | `pyproject.toml` against `uv.lock` | yes |
| Formatting | `ruff format --check` | all Python in the repo | yes |
| Lint | `ruff check` | all Python in the repo | yes |
| Types | `mypy --strict` | `Tools/mcp`, `Tools/audio`, `Tools/tests` | yes |
| Tests | `pytest` (parallel, warnings are errors) | `Tools/tests` | yes |
| Formatting (C++) | `clang-format --dry-run --Werror` with `.clang-format` | `Source/`, C++ and C# | no |
| Build (C++) | Unreal Build Tool, `BeaconEditor Win64 Development` | `Source/`; a warning in it fails the gate | no |
| Tests (C++) | Unreal automation tests under `Beacon.`, in a windowless editor | `Source/BeaconEditor/Private/Tests`; a test that passes with a warning fails the gate | no |

## The C++ gates run only where the engine is

The three C++ gates are in `Tools/verify-cpp.ps1`. `verify.ps1` runs them when it finds Unreal Engine 5.8 at `C:\Program Files\Epic Games\UE_5.8`, or at `$env:UE_ROOT`, and prints that it skipped them otherwise. A GitHub-hosted runner has neither the engine nor its compiler, so **CI does not cover them: run the canonical command locally before pushing a change under `Source/`**. Review this if the project gets a self-hosted runner with the engine installed.

- The build gate does nothing when the binaries are current, which is the usual case and works with the editor open. When it has something to compile, the editor must be closed: Live Coding holds the build lock while it runs.
- The tests gate starts a second editor with no window (`-nullrhi`, MCP port 8017), so it also works with the editor open. It takes about 40 seconds.
- `clang-format` is taken from `PATH`, or from Visual Studio's "C++ Clang tools for Windows" component. It is not pinned: a different version can format differently. Version 22.1.3 formatted the current source. Pinning it through `uv` would also let CI run this gate.

## Exceptions

- **`C4996` deprecation warnings from engine headers.** Compiling the shared precompiled header with MSVC 14.51 prints 29 of them, all in Epic's headers (for example `UObject/Class.h`), along with the notice "Visual Studio compiler 14.51 is not a preferred version". UE 5.8 prefers MSVC up to 14.50. They appear only when the precompiled header is rebuilt, and they are why the build cannot use `-WarningsAsErrors`: with it the engine's own header fails. The build gate writes compiler output to `Saved/Logs/verify-build.log` and fails on any warning whose path is under this repo's `Source/`, so the project's own code is held to zero warnings. Review this when MSVC 14.50 is installed beside 14.51 or the engine is updated.

## Gates that do not apply, or are not set up

- **Types for `Tools/editor_python`.** Those scripts run inside the editor's interpreter and import `unreal`, which exists only there. They are formatted and linted but not type checked. Review this if Epic publishes type stubs that can be installed outside the editor.
- **Static bug analysis for Python.** Ruff's `B`, `S`, `PL` and `RUF` rule sets cover it.
- **Static bug analysis for C++. Not set up.** Unreal Build Tool can run MSVC's analyser (`-StaticAnalyzer=VisualCpp`), but it has not been tried on this project. The compiler's warnings are the only analysis the C++ gets.
- **Vulnerability and package checks.** The tooling has no runtime dependencies, and the C++ depends only on the engine. The development tools are pinned in `uv.lock`.
- **Game build and packaging.** The build gate compiles the editor target. The game target is first built when the game is packaged, which arrives with #18.

## Game content

Blueprints, levels and data assets cannot be checked from a shell. They are verified in the running editor with the verify loop in [verify-loop.md](verify-loop.md): play in editor, drive the game, read the log, capture a screenshot. A whole night can be played and reported without a person with [night-playtest.md](night-playtest.md).
