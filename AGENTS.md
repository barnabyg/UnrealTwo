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

### Verification

One command checks the repo's tooling: `pwsh Tools/verify.ps1`. See `docs/agents/verification.md`.

### Checking game changes

Play-in-editor checks are driven through the MCP with no person at the editor. See `docs/agents/verify-loop.md`.
