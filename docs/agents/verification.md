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
| Formatting (C++) | `clang-format --dry-run --Werror` with `.clang-format` | `Source/`, C++ and C# | yes |
| Build (C++) | Unreal Build Tool, `BeaconEditor Win64 Development` | `Source/`; any warning fails the gate, apart from the exception below | no |
| Tests (C++) | Unreal automation tests under `Beacon.`, in a windowless editor | `Source/BeaconEditor/Private/Tests`; a test that passes with a warning fails the gate | no |

## The C++ build and tests run only where the engine is

The C++ formatting gate runs everywhere: `clang-format` is a development dependency pinned in `uv.lock`, so every machine and CI format with the same version. The build and tests gates are in `Tools/verify-cpp.ps1`. `verify.ps1` runs them when it finds Unreal Engine 5.8 at `C:\Program Files\Epic Games\UE_5.8`, or at `$env:UE_ROOT`, and prints that it skipped them otherwise. A GitHub-hosted runner has neither the engine nor its compiler, so **CI does not cover them: run the canonical command locally before pushing a change under `Source/`**. Review this if the project gets a self-hosted runner with the engine installed.

- The build gate compiles nothing when the binaries are current, which is the usual case and works with the editor open; it then prints "up to date: nothing was compiled". The compiler only prints a warning when it compiles the file, so an up-to-date run proves nothing about warnings: the gate that counts is the one that follows a change under `Source/`. When there is something to compile, the editor must be closed, because it has the modules' DLLs loaded and Live Coding holds the build lock.
- The tests gate starts a second editor with no window (`-nullrhi`, MCP port 8017), so it also works with the editor open. It takes about 40 seconds.

## Exceptions

- **`C4996` deprecation warnings from engine headers.** Compiling the shared precompiled header with MSVC 14.51 prints 29 of them, all in Epic's headers (for example `UObject/Class.h`), along with the notice "Visual Studio compiler 14.51 is not a preferred version". UE 5.8 prefers MSVC up to 14.50. They appear only when the precompiled header is rebuilt, and they are why the build cannot use `-WarningsAsErrors`: with it the engine's own header fails. The build gate writes the build's output to `Saved/Logs/verify-build.log` and fails on every warning in it except these two: a `C4996` whose file is under the engine's folder, and that notice. Review this when MSVC 14.50 is installed beside 14.51 or the engine is updated.

## Gates that do not apply, or are not set up

- **Types for `Tools/editor_python`.** Those scripts run inside the editor's interpreter and import `unreal`, which exists only there. They are formatted and linted but not type checked. Review this if Epic publishes type stubs that can be installed outside the editor.
- **Static bug analysis for Python.** Ruff's `B`, `S`, `PL` and `RUF` rule sets cover it.
- **Static bug analysis for C++ is a manual check, not a gate.** Unreal Build Tool runs MSVC's analyser when the build command is given `-StaticAnalyzer=VisualCpp`. On 2026-11-24 it analysed every file under `Source/` in 90 seconds and reported nothing. It is not in the script because an analysis run invalidates the ordinary build: the next build compiles and links everything again, which fails while the editor is open and would make every verify run a full rebuild. Run it by hand, with the editor closed, after a substantial change to the C++, and run the ordinary build afterwards. Review this if a later engine version keeps the two builds apart.
- **Lint for C++.** There is no separate linter; the compiler's warnings and the analyser above are what the C++ gets. `clang-tidy` ships with Visual Studio but needs a compilation database that this project does not generate.
- **Vulnerability and package checks.** The tooling has no runtime dependencies, and the C++ depends only on the engine. The development tools, `clang-format` among them, are pinned in `uv.lock`.
- **Game build and packaging.** The build gate compiles the editor target only. The game target is compiled when the game is packaged with `pwsh Tools/package.ps1` ([packaging.md](packaging.md)), which takes about two minutes, needs the engine, and is not a gate. Run it after a change under `Source/Beacon` or a change to which content is cooked, and read the packaged game's log: some problems show only in a cooked build (finding F-069).

## Game content

Blueprints, levels and data assets cannot be checked from a shell. They are verified in the running editor with the verify loop in [verify-loop.md](verify-loop.md): play in editor, drive the game, read the log, capture a screenshot. A whole night can be played and reported without a person with [night-playtest.md](night-playtest.md).
