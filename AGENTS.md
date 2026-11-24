# AGENTS.md

Guidance for AI coding agents working in this repository.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues on `barnabyg/UnrealTwo`, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Unreal MCP

How to launch the editor and connect: `docs/agents/unreal-mcp.md`. Before building anything, read `docs/mcp/capability-map.md` for which toolset covers what, and `docs/mcp/tool-inventory.md` for every tool the server reports. Append what happened to `docs/mcp/findings-log.md`, using its entry format.

### C++ and custom MCP tools

The game is Blueprint. `Source/BeaconEditor` is an editor-only C++ module that adds the project's own MCP tools; `SimulateWave` predicts a night from the wave and turret data. A change under `Source/` needs a build with the editor closed and an editor restart. See "Launch the editor" and "Adding a custom tool" in `docs/agents/unreal-mcp.md`.

### Verification

One command checks the repo's tooling and C++: `pwsh Tools/verify.ps1`. CI checks the C++ formatting but cannot build or test it, so run the command locally before pushing a change under `Source/`. See `docs/agents/verification.md`.

### Checking game changes

Play-in-editor checks are driven through the MCP with no person at the editor. See `docs/agents/verify-loop.md`. To play a whole night with a given turret layout and get its outcome, see `docs/agents/night-playtest.md`. What was measured for each ticket's acceptance criteria is in `docs/mcp/pie-verification.md`; add to it when a ticket is verified.
