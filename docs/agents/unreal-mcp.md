# Unreal MCP (Unreal Editor ↔ Claude Code)

UE 5.8 ships an experimental MCP server inside the editor process. Claude Code reaches it through `.mcp.json` at the repo root (`unreal-mcp` → `http://127.0.0.1:8000/mcp`, streamable HTTP; stdio is not supported).

## Enable in the project (once the `.uproject` exists)

1. In the editor, open **Edit > Plugins** and enable **Unreal MCP** (`ModelContextProtocol`) and **All Toolsets** (`AllToolsets`). Toolset Registry comes in as a dependency. Restart the editor when it asks.
2. The server starts automatically with the editor. Settings are in **Editor Preferences > Agentic Workflows > Model Context Protocol**: Auto Start Server, Server Port Number (8000), Server URL Path (`/mcp`).
3. Check the Output Log (category `LogModelContextProtocol`) for the bind address and port.

Equivalent `.uproject` entries:

```json
{ "Name": "ModelContextProtocol", "Enabled": true },
{ "Name": "AllToolsets", "Enabled": true }
```

You don't need **MCP Client Toolset**. It is for the editor acting as an MCP *client*.

## Connect

- Start the editor and wait for it to finish loading. Then start `claude` from the repo root and approve the `unreal-mcp` project server. If it doesn't connect, reconnect with `/mcp`.
- Health check: a `GET` on `http://127.0.0.1:8000/mcp` returns **405** while the server is up.
- Use the full `/mcp` path. Pointing a client at bare `:8000` drops the connection.

## Useful console commands

- `ModelContextProtocol.StartServer [port]` / `ModelContextProtocol.StopServer`
- `ModelContextProtocol.RefreshTools` to pick up new tools, then reconnect. New C++ `UFUNCTION` tools need an editor restart; Live Coding is not enough.
- `ModelContextProtocol.GenerateClientConfig ClaudeCode`

## Caveats

- There is no authentication. The server is loopback-only by default (`[HTTPServer.Listeners] DefaultBindAddress=127.0.0.1`), so don't widen it or add allowed origins.
- Tool calls run one at a time on the game thread. Claude Code gives up on a single call after about 120 s.
- If `list_toolsets` only returns `AgentSkillToolset`, the toolset plugins aren't enabled.
- A second editor needs another port (`-ModelContextProtocolPort=8001`) and a second `.mcp.json` entry.
