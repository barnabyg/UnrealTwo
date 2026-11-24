# Unreal MCP (Unreal Editor ↔ Claude Code)

UE 5.8 ships an experimental MCP server inside the editor process. Claude Code reaches it through `.mcp.json` at the repo root (`unreal-mcp` → `http://127.0.0.1:8000/mcp`, streamable HTTP; stdio is not supported).

## Launch the editor

Binary assets (`.uasset`, `.umap`) are stored in Git LFS. In a fresh clone, run `git lfs install` and then `git lfs pull` once to fetch them. Then:

```powershell
Set-Location C:\docs\git\UnrealTwo; & "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "$PWD\Beacon.uproject"
```

The MCP server starts with the editor and answers within about a minute.

## How the project is set up

`Beacon.uproject` is a Blueprint-only project built from the Third Person Blueprint template: the template's content plus the shared `Characters`, `Input` and `LevelPrototyping` packs, copied under `Content/`. Three things make the MCP work:

1. **Plugins.** `Beacon.uproject` enables **Unreal MCP** (`ModelContextProtocol`) and **All Toolsets** (`AllToolsets`). Toolset Registry comes in as a dependency.
2. **Auto start.** The engine default for Auto Start Server is **off**. `Config/DefaultEditorPerProjectUserSettings.ini` turns it on for this project. Passing `-ModelContextProtocolStartServer` on the editor command line does the same for one run.
3. **Asset manager rule.** All Toolsets pulls in the Game Features plugin, which logs a load error on every start unless the asset manager has a rule for `GameFeatureData`. `Config/DefaultGame.ini` adds one.

The settings are per-user editor preferences, under **Editor Preferences > Agentic Workflows > Model Context Protocol**: Auto Start Server, Server Port Number (8000), Server URL Path (`/mcp`), and Enable Tool Search.

You don't need **MCP Client Toolset**. It is for the editor acting as an MCP *client*. All Toolsets enables it anyway.

## Connect

- Start the editor and wait for it to finish loading. Then start `claude` from the repo root and approve the `unreal-mcp` project server. A session that was already running reconnects by itself on the next tool call; if it doesn't, reconnect with `/mcp`.
- Health check: a `GET` on `http://127.0.0.1:8000/mcp` returns **405** while the server is up.
- Use the full `/mcp` path. Pointing a client at bare `:8000` drops the connection.
- In the Output Log, `LogModelContextProtocol` reports the port ("Starting MCP server on port 8000") and `LogHttpListener` reports the bind address ("Created new HttpListener on 127.0.0.1:8000").

## How tools are exposed

With Enable Tool Search on (the default), the server registers only three tools: `list_toolsets`, `describe_toolset` and `call_tool`. Every toolset tool is reached through `call_tool` after reading its schema with `describe_toolset`. With All Toolsets enabled, `list_toolsets` returns 52 toolsets.

## Useful console commands

- `ModelContextProtocol.StartServer [port]` / `ModelContextProtocol.StopServer`
- `ModelContextProtocol.RefreshTools` to pick up new tools, then reconnect. New C++ `UFUNCTION` tools need an editor restart; Live Coding is not enough.
- `ModelContextProtocol.GenerateClientConfig ClaudeCode`

## Expected log noise

A clean start has no errors. These lines are expected and need no action:

- `LogModelContextProtocol: Error: Call to unknown method "server/discover"` appears each time Claude Code connects. The client probes a method the server doesn't implement, then connects normally.
- `LogModelContextProtocol: Warning: Data transmitted via this plugin ... is Licensed Technology under the UE EULA` is a notice printed on every start.
- `LogSemanticSearch: OpenAIEmbeddingProvider created (... API KEY MISSING ...)` comes from the Semantic Search toolset. With no key it sends nothing. Don't add a key without deciding that project content may go to that service.

## Caveats

- There is no authentication. The server is loopback-only by default (`[HTTPServer.Listeners] DefaultBindAddress=127.0.0.1`), so don't widen it or add allowed origins.
- Tool calls run one at a time on the game thread. Claude Code gives up on a single call after about 120 s.
- If `list_toolsets` only returns `AgentSkillToolset`, the toolset plugins aren't enabled.
- After an editor crash, the next launch can stop on a "Restore Packages" dialog. The MCP server does not start until someone answers it, so the health check is refused while the process runs. `(Get-Process UnrealEditor).MainWindowTitle` shows the dialog's title. See finding F-054 in `docs/mcp/findings-log.md` for how to get past it.
- A second editor needs another port (`-ModelContextProtocolPort=8001`) and a second `.mcp.json` entry.
