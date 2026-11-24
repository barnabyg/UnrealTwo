# Unreal MCP (Unreal Editor ↔ Claude Code)

UE 5.8 ships an experimental MCP server inside the editor process. Claude Code reaches it through `.mcp.json` at the repo root (`unreal-mcp` → `http://127.0.0.1:8000/mcp`, streamable HTTP; stdio is not supported).

## Launch the editor

Binary assets (`.uasset`, `.umap`) are stored in Git LFS. In a fresh clone, run `git lfs install` and then `git lfs pull` once to fetch them.

The project has C++ modules, and their binaries are not in Git. Build them before the first launch and after any change under `Source/`, with the editor closed:

```powershell
Set-Location C:\docs\git\UnrealTwo; & "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" BeaconEditor Win64 Development "-Project=$PWD\Beacon.uproject" -WaitMutex
```

The build needs Visual Studio with the "Desktop development with C++" workload. A first build takes about a minute. The editor cannot load the project's modules without it, so a launch from a clone that was never built does not reach the MCP server.

Then launch:

```powershell
Set-Location C:\docs\git\UnrealTwo; & "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "$PWD\Beacon.uproject"
```

The MCP server starts with the editor and answers within about a minute.

## How the project is set up

`Beacon.uproject` was built from the Third Person Blueprint template: the template's content plus the shared `Characters`, `Input` and `LevelPrototyping` packs, copied under `Content/`. The game is still all Blueprint. `Source/` holds two C++ modules: `Beacon`, an empty runtime module that the game target needs in order to link, and `BeaconEditor`, an editor-only module that holds the project's own MCP tools (see "Adding a custom tool"). Three things make the MCP work:

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

## Adding a custom tool

A tool is a static C++ function on a toolset class. The project's own toolset is `UBeaconBalanceToolset` in `Source/BeaconEditor/Private/BeaconBalanceToolset.h`, which the server lists as `BeaconEditor.BeaconBalanceToolset` (the module name, then the class name without its `U`). Its one tool, `SimulateWave`, is the worked example for every step below.

1. **Write the function.** In a class derived from `UToolsetDefinition`, declare a `static` function with `UFUNCTION(meta = (AICallable), Category = "...")`. To start a new toolset, add a class and register it in the module's `StartupModule` with `UToolsetRegistry::RegisterToolsetClass` (see `BeaconEditorModule.cpp`). A new module also needs `ToolsetRegistry` in its `Build.cs` dependencies.
2. **Document it in the comment.** The server builds the tool's description and schema from the code: the function's doc comment is the description, each `@param` line describes an argument, and each `UPROPERTY` comment describes a field. Write them for an agent that has never seen the project.
3. **Use structs for structured input and output.** A `USTRUCT(BlueprintType)` whose fields are `UPROPERTY(BlueprintReadWrite)` or `BlueprintReadOnly` becomes a JSON object, an array of them a JSON array, and a `UENUM` a string with its allowed values listed. Names start with a lower-case letter in JSON (`TotalCreatures` is `totalCreatures`). The return value arrives as `returnValue`.
4. **Report bad input as an error, not a crash.** Call `UKismetSystemLibrary::RaiseScriptError` with a sentence that says what was wrong and what is allowed, then return a default value. The caller receives that sentence as the tool error. Check every argument before using it: a missing struct field arrives as its default, and a value of the wrong type can arrive as zero. The function runs on the editor's main thread, so bound anything slow: the editor is frozen until it returns.
5. **Test it.** Automation tests live in `Source/BeaconEditor/Private/Tests`. Keep the logic in plain functions that a test can call without the editor's data, and use `UE::ToolsetRegistry::FToolCallExceptionHandler::CaptureErrorsIn` to test a raised error.
6. **Build with the editor closed**, using the build command under "Launch the editor". No MCP tool compiles code. While the editor is open Live Coding holds the build lock, and Live Coding cannot add a new `UFUNCTION`.
7. **Restart the editor.** Save first, or it stops on a save prompt. `python Tools/mcp/beacon_mcp.py console QUIT_EDITOR` closes it; launch it again from a shell. The new tool is in `list_toolsets` and `describe_toolset` as soon as the server answers. No `ModelContextProtocol.RefreshTools` was needed after a restart, and Claude Code reconnects on its next call.
8. **Check it over the MCP.** Read the schema with `describe_toolset`, call the tool with good and bad input, and run `pwsh Tools/verify.ps1`.

A tool can read Blueprint-defined data without C++ headers for it by looking properties up by name on the loaded object. `BeaconBalanceData.cpp` does this for the wave, creature and turret data assets. It reads the objects as loaded, so an edit made with `ObjectTools.set_properties` counts before it is saved.

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
- A second editor needs another port (`-ModelContextProtocolPort=8001`) and a second `.mcp.json` entry. The verify script starts a windowless one on port 8017 to run the C++ tests.
