# What the UE 5.8 Unreal MCP can do

An evaluation drawn from building Beacon, a small third-person wave defence game, through the experimental MCP server that ships inside the UE 5.8 editor. Tickets #2 to #18 built the game. Each one recorded what it tried in the [findings log](findings-log.md), and the F-numbers below point at those entries. The planned coverage is in the [capability map](capability-map.md), and the server's tools are listed in the [tool inventory](tool-inventory.md).

This report is for someone who has never used the MCP and has to decide what to trust it with. The short answer: it is a capable Blueprint and asset author, a usable play-in-editor driver once you add a few workarounds, and blind to anything outside the editor's object model. It cannot build, cook or package. Most of its failures are silent: a call returns success and does nothing.

## How it was tested

- **Setup.** UE 5.8.3 on Windows 11, with the Unreal MCP and All Toolsets plugins: 52 toolsets behind three meta-tools (`list_toolsets`, `describe_toolset`, `call_tool`). The project added a 53rd, its own C++ toolset. The client was Claude Code. Setup is in [unreal-mcp.md](../agents/unreal-mcp.md).
- **Rule.** Build through the MCP wherever a tool exists. Fall back, in this order, to another MCP tool, editor Python, C++, then a manual step. Log every fallback and failure.
- **Result.** A packaged game with a level, AI with behaviour trees and an EQS query, data-driven waves, turrets, menus, a HUD, effects, sound, PCG scatter, an intro sequence and saving. Each feature was checked in play-in-editor through the MCP ([pie-verification.md](pie-verification.md)). 69 findings were logged in all, F-001 to F-069.

## Ratings

- **Worked:** the toolset did the job as documented, with no workaround worth a warning.
- **Worked with caveats:** the job got done through the MCP, but only with a workaround, a second tool, or after a silent failure that had to be spotted.
- **Did not work:** no tool for the job, or the tools could not finish it. A fallback outside the MCP's own tools did the work, or nothing did.

| Capability | Rating | Justification | Findings |
|---|---|---|---|
| Level and actor editing | Worked with caveats | Placing, moving, tagging and deleting actors works. No tool creates a level, so the template was duplicated. Three silent failures matter: `set_actor_transform` resets a scale it was not given, `save_assets` on a map skips changed actors, and collision settings set with `ObjectTools` do not apply. A Blueprint component change does not reach an actor already placed. | F-001, F-002, F-004, F-006, F-008, F-009, F-010, F-015, F-033 |
| Landscape | Did not work | No landscape tool exists. The island was built from engine primitives instead, which the project allowed, so no landscape route was tried. | F-006; [tool-inventory.md](tool-inventory.md) |
| PCG | Worked with caveats | The whole scatter graph was built node by node and seeded through the MCP. A spawner's mesh list is not a node parameter and needs `ObjectTools`; one schema names pins that do not exist; no tool returns the generated instances. | F-046, F-047 |
| Blueprint graph authoring | Worked with caveats | The strongest toolset. The graph DSL wrote every gameplay graph in the game. It also has the most traps: it cannot write Enhanced Input action events, it silently drops positional arguments and picks wrong overloads, rewriting an event leaves the old nodes in the graph, and reading a graph marks the Blueprint unsaved. Check pin values with `get_node_infos` after every write. | F-007, F-012, F-018, F-022, F-023, F-024, F-025, F-026, F-029, F-038, F-039, F-044, F-050, F-055, F-061, F-063 |
| Enhanced Input | Worked with caveats | No dedicated tool, but input actions and mapping contexts are data assets that `DataAssetTools` and `ObjectTools` author. Triggers and modifiers are instanced objects and were left empty; setting them was not tried. Action events need node tools, not the DSL. | F-021, F-022, F-050 |
| Animation Blueprint | Did not work | No tool edits an AnimGraph or a state machine. Beacon reused the template's animation Blueprint, so this was never needed and never tried beyond the inventory. | [capability-map.md](capability-map.md) |
| NavMesh | Worked with caveats | Generic scene and settings tools place and configure the bounds volume. The rebuild needs a console command typed through the Slate inspector. | F-016, F-020 |
| Behaviour Tree and StateTree | Did not work | Both toolsets only inspect. Editor Python built every tree; the inspect tools then confirmed the result. | F-017, F-031, F-034 |
| EQS | Did not work | No tool, and no scripted route at all: the query's parts can be created but not joined, because the properties are protected. A person made the query in the EQS editor. | F-030, F-034 |
| DataTables and DataAssets | Worked with caveats | Data assets with Blueprint-defined classes covered every need, including a C++ tool reading them. No tool creates a row struct, so DataTables stayed out of reach. | F-028, F-059 |
| UMG | Worked | Widget Blueprints, widget trees, layout, fonts, click events, a progress bar and widgets made at run time all came from `UMGToolSet`, `ObjectTools` and the DSL. The Slate inspector reads and clicks the result during play. | F-019, F-035, F-037 |
| Materials | Worked with caveats | Material graphs and instances were authored fully. Reparenting an instance does not mark it unsaved, so it needed a forced save from editor Python. A usage flag the editor sets for itself was missing in the cooked build, which only the packaged game's log showed. | F-006, F-041, F-069 |
| Niagara | Worked with caveats | Systems made from engine templates were trimmed and tuned through stack inputs, and compiled clean. A system needs a template to start from, and results run to 15,000 characters per emitter, too large to read without a script client. | F-042 |
| Audio | Did not work | No tool imports or authors sound. Sounds were synthesised by a script and imported with editor Python. Nothing can confirm that they are heard. | F-043 |
| Lighting | Worked with caveats | No dedicated tool, but lights are actors and components that the scene, actor and object tools handle, and graphs switch them at run time. The project uses dynamic lighting only, so there was no lighting build to run. | F-032, F-033, F-065 |
| Sequencer | Worked with caveats | The intro shot was authored with the Sequencer toolsets alone. Binding a camera silently adds a Camera Cut track, which fought the game for the view until it was removed. | F-048, F-049 |
| SaveGame | Worked with caveats | No dedicated tool; a SaveGame Blueprint and ordinary graphs do it, and saving works in the packaged build. Blueprint cannot guard against a file that is not a save, which crashes the engine on load. | F-052, F-053, F-067 |
| PIE control | Worked with caveats | Start and stop are tools. Everything else is a workaround: input is console commands typed through the Slate inspector, game state is read with editor Python, options go through the `open` console command, and the background frame-rate throttle has to be off for combat to mean anything. | F-013, F-027, F-037, F-045, F-051, F-056, F-061, F-062 |
| Log reading | Worked | `GetLogEntries` filters by category and pattern. It was how every run was checked and how long jobs were polled. Results can be large. | F-005, F-061, F-066 |
| Viewport screenshots | Worked with caveats | `CaptureViewport` renders the editor world even during play, so it cannot show the game, and it needs two arguments its schema marks optional. The Slate inspector's `Screenshot` of the viewport panel shows the game. | F-005, F-014 |
| Custom C++ tools | Worked with caveats | No tool scaffolds a project module or compiles code, and the editor must restart. After that, a C++ function is a tool like any other, with a schema taken from its comments, and the automation toolset runs its tests. | F-057, F-058, F-059, F-060 |
| Packaging | Did not work | No build, cook or package tool. The editor's own Cook Content menu can be clicked through the Slate inspector, which starts a cook in the background. Package Project was not clicked: its tooltip says it archives to a user-selected directory, which means a native folder dialog that no tool could answer. The build is made by `RunUAT BuildCookRun` from a shell, and the packaged game has no MCP server to check it with. | F-065, F-066, F-067 |
| Agent workflow | Worked with caveats | There is no tool for console commands or editor Python; both are typed into the editor's `Cmd` box through the Slate inspector. That route reaches almost anything, but it is slow (about three seconds a call), cannot pass a value back except through the log, and a modal dialog it opens stops the server. `set_properties` fails silently when given an object instead of a JSON string. | F-003, F-036, F-040, F-051, F-054, F-064, F-068 |

## Fallbacks used

Every time a job left the MCP's own tools, and why.

| Fallback | Used for | Why the MCP could not do it | Findings |
|---|---|---|---|
| Another MCP tool | Duplicating the template level | No tool creates a level | F-002 |
| Another MCP tool (Slate inspector) | Console commands and editor Python | No tool runs either | F-003 |
| Another MCP tool | Stripping a mesh's collision, and per-channel responses in a graph | `ObjectTools` cannot change collision settings | F-008 |
| Another MCP tool | `save_assets` on the map instead of `save_actor` | `save_actor` fails on one-file-per-actor levels | F-010 |
| Another MCP tool (Slate screenshot) | Pictures of the running game | `CaptureViewport` renders the editor world | F-014 |
| Another MCP tool (console) | `RebuildNavigation` | No NavMesh tool | F-016 |
| Another MCP tool (node tools) | Enhanced Input action events, delegate binding | The DSL cannot write them | F-022, F-050 |
| Another MCP tool (BeginPlay graph) | Camera boom offset | Properties on an inherited component do not reach the game | F-023 |
| Another MCP tool (data assets) | Waves and turret types | No tool creates a DataTable row struct | F-028 |
| Another MCP tool | Re-placing the lighthouse | Component changes do not reach a placed actor | F-033 |
| Another MCP tool (`ObjectTools`) | A PCG spawner's mesh lists | Not a node parameter | F-046 |
| Editor Python | Reading game state during play, frame rate, timing traces | No tool reads the PIE world | F-013, F-045, F-051 |
| Editor Python | Saving levels, actors and a material instance | `save_assets` skips packages that are not marked dirty | F-015, F-041 |
| Editor Python | Saving only Beacon's own packages | `read_graph_dsl` marks the template Blueprints it reads as unsaved | F-024 |
| Editor Python | Building behaviour trees | Behaviour tree tools inspect only | F-017, F-031 |
| Editor Python | Putting the game in a state for a test | A Blueprint variable cannot be set from Python during play | F-040 |
| Editor Python | Importing sounds | No audio tool | F-043 |
| Editor Python | Reading generated PCG instances | No tool returns them | F-047 |
| C++ | The project's own MCP tool | No tool scaffolds a module or compiles | F-057 |
| Another MCP tool (Slate inspector) | Starting a cook from the editor's Platforms menu, polled from the log | No cook tool | F-066 |
| Another MCP tool (console) | `RecompileShaders changed` | No shader tool | F-065 |
| Shell (`RunUAT`) | The packaged build | No build, cook or package tool, and Package Project's folder dialog would block the editor | F-066 |
| The game's command line and log | Automated nights in the packaged game | The packaged game has no MCP server | F-067 |
| Win32 input and screen capture from a script | Playing the packaged game through its menus | The packaged game has no MCP server, and the computer-use tool could not be granted its window | F-067 |
| Manual step | The EQS query | No scripted route joins a query's parts | F-030, F-034 |
| Shell, then relaunch | Getting past a modal dialog after a crash or a reload | Every tool lives in the blocked editor process | F-054, F-064 |
| Script client | Large results, screenshots to file, playtests, orphan nodes | Results too large for an agent's context; jobs longer than one call | F-005, F-042, F-055, F-056, F-062 |

## Reliability and ergonomics

### Silent failures

The most expensive problem. These calls returned success and did nothing, or did something else:

- `ObjectTools.set_properties` on collision settings (F-008), on an inherited component (F-023), on a placed actor's component (F-033), and with its values sent as an object instead of a JSON string (F-036).
- `ActorTools.set_actor_transform` reset an omitted scale, against its own schema (F-009).
- `AssetTools.save_assets` on a map with changed actors (F-015) and on a reparented material instance (F-041).
- The graph DSL dropped positional arguments and picked a wrong overload (F-025), and left old nodes behind on a rewrite (F-055).
- Sequencer added a Camera Cut track it did not report (F-049).
- `SlateInspectorToolset.Click` returned true on a disabled button (F-037), and once on a window that had just been restored (F-056).

The working rule: read back every change through a different path than the one that wrote it, and check `git status` after every save.

### Errors that are wrong

- `CaptureViewport` demands two arguments its schema marks optional (F-014).
- The PCG schema lists pins that do not exist for some operations (F-046).
- A struct field the schema marks required arrives as zero when left out; the server does not enforce the schema (F-058).
- `AutomationTestToolset.RunTestsByFilter` reports an error when every test passed, because tests that raise errors on purpose leak them into the call (F-060).

### The per-call limit

Claude Code gives up on a single call after about 120 seconds, and the editor is frozen for the length of every call. The project never ran a long job as a single call. Each was started, left to run, and polled:

- **A night of play** (one to two minutes): start it with a console command, return, and poll the log every 20 seconds for a result line (F-061, `night_playtest.py`).
- **A cook** (93 seconds): clicking Cook Content returns in 0.18 s and UAT runs in its own process; its output arrives in the editor log as `UATHelper` lines, which `GetLogEntries` polls (F-066).
- **Packaging** (see F-066): run from a shell, outside the MCP, because no tool can start it.
- **Custom tools** have to bound their own work, since the editor is frozen while they run. `SimulateWave` caps its input and its iterations (F-057, F-058).

### One at a time

Tool calls run one at a time on the editor's game thread. Consequences seen:

- The editor runs at about 3 frames a second in the background, and a turret fires at most once a frame, so a night's outcome depended on the throttle (F-062). Turn `bThrottleCPUWhenNotForeground` off for anything timing-sensitive.
- A game-state read through the console costs about three seconds (F-051), too slow to time short events; slow motion (F-027) or a per-frame callback in editor Python (F-051) works around it.
- **Nothing stops two agents sharing one editor.** During #18 a second agent session quit and relaunched the editor in the middle of this session's menu clicks, and this session's calls failed with a refused connection (F-068). Give each agent its own editor and port, or one at a time.

### Restarts and blocked editors

- New C++ tools need a build with the editor closed and a restart; Live Coding is not enough (F-057, F-058).
- After a crash the editor stops on a Restore Packages dialog, and the server never starts (F-054).
- `reload_packages` from editor Python opened a modal window and the server stopped answering (F-064).
- An unsaved package makes `QUIT_EDITOR` wait on a save prompt no tool can answer (F-058, F-064).
- A minimised editor answers every call but its Slate snapshot is empty, so nothing can be clicked or typed (F-056).
- A native OS dialog, such as the folder picker that Package Project's tooltip implies, would block the game thread the same way. It was avoided rather than tried (F-066).

The pattern in each case: every tool lives inside the editor process, so anything that blocks that process takes the whole MCP down, and only a shell can recover it.

### Ergonomics

- **Discovery is good.** `describe_toolset` gives full schemas; the DSL's node ids are found with `find_node_types`. Tool descriptions are mostly accurate, apart from the cases above.
- **Results are large.** `describe_toolset` on `BlueprintTools` is 72,000 characters; Niagara reads run to 15,000; screenshots arrive as base64 in the JSON. A small script client (`Tools/mcp/beacon_mcp.py`) that saves images and filters output was needed from the third ticket on (F-005).
- **Naming is inconsistent.** Property names are lower-camel in results and matched without case on input (F-006); DSL ids differ inside and outside a class and drop `b` from booleans (F-029, F-039); an event's DSL name is not its function name (F-018).
- **Adding a tool is easy once C++ is in place.** One static function with a doc comment becomes a well-described tool (F-058).

## Recommendations

### Use the MCP for

- Blueprint authoring through the graph DSL, followed by a pin-level read-back.
- UMG, Materials, Niagara from templates, PCG graphs, Sequencer, data assets, Enhanced Input assets, and project settings through `ConfigSettingsToolset` (F-011).
- Play-in-editor checks: start, drive through console commands, read the log, take a Slate screenshot, stop. Wrap them in a script.
- Project-specific tools written in C++, such as a balance simulator that answers in milliseconds instead of a minute of play.
- Starting long editor jobs that the editor already runs in the background (a cook) and polling the log for the result.

### Avoid, or check by another route

- Trusting a `true` from `set_properties`, `set_actor_transform` or `save_assets`. Read back and check `git status`.
- Rewriting graphs without running an orphan-node check afterwards.
- Behaviour trees, EQS, audio, animation graphs, landscape and DataTable row structs: no tool. Plan editor Python or a person.
- Anything that can raise a modal or native dialog: reloading packages, quitting with unsaved changes, Package Project, a crash. Each one stops the server.
- Sharing one editor between agents.
- Timing or balance measurements with the editor in the background.

### Raise with Epic

1. **Silent success.** `set_properties`, `set_actor_transform` and `save_assets` should report when nothing changed or was written, and `set_actor_transform` should honour its schema's "unset means unchanged" (F-008, F-009, F-015, F-036, F-041).
2. **A console and Python tool.** Typing into the `Cmd` box through UI automation is the single most used workaround in this project (F-003).
3. **Build, cook and package tools** that start the job, return a handle, and report progress and result, so long jobs fit the per-call limit (F-066).
4. **Authoring for Behaviour Trees, StateTree and EQS**, which today are inspect-only or absent (F-017, F-030).
5. **A play-in-editor input and state tool**, and a `CaptureViewport` that shows the game during play (F-013, F-014).
6. **Dialog safety.** Modal and native dialogs stop the server with no way to answer them; tools should refuse to open one, or the server should run off the game thread (F-054, F-064, F-066).
7. **The graph DSL**: Enhanced Input events, named exec outputs in read-back, positional arguments, and removing replaced nodes (F-022, F-025, F-055).
8. **`read_graph_dsl` should not mark a Blueprint dirty** (F-024, F-063).
9. **Schema accuracy**: optional arguments that are required, pins that do not exist, and required fields that are not enforced (F-014, F-046, F-058).
10. **Concurrency**: a way to tell that another client is driving the editor, or a session lock (F-068).
