# Unreal MCP capability map

For each Beacon feature area: which toolset covers it, or the fallback when nothing does. It was written from the live tool list in [tool-inventory.md](tool-inventory.md) on 2026-11-23, before the features were built. What actually happened is in [findings-log.md](findings-log.md); when the two disagree, the findings log is right.

**Covered** means a toolset can author the thing. **Partly covered** means tools exist but miss a step Beacon needs. **Not covered** means no tool can author it.

## Fallbacks, in order of preference

1. **Another MCP tool.** Generic tools reach a long way: `ObjectTools.set_properties` edits any editable property, `DataAssetTools.create` makes any `UDataAsset` subclass, and `BlueprintTools.write_graph_dsl` can call most gameplay functions.
2. **Editor Python**, run through the MCP by typing `py "<script>"` into the editor's console box with the Slate inspector (finding F-003). Scripts live in `Tools/editor_python/`.
3. **C++**, which needs a compiler, a project module and an editor restart. Beacon is a Blueprint-only project, so this is a last resort.
4. **A manual step** by a person in the editor.

## Map

| Feature area | Status | Toolset | Gap and fallback |
|---|---|---|---|
| Level and actor editing | Partly covered | `SceneTools`, `ActorTools`, `PrimitiveTools`, `ObjectTools` | Placing, moving, tagging, parenting and deleting actors are covered. There is no tool to create a level: duplicate the template level with `AssetTools.duplicate` (F-002). |
| Landscape | Not covered | none | No landscape tool. The island is built from engine primitives, which the ticket allows. |
| PCG | Covered | `PCGToolset`, `PCGSpatialToolset` | Graph authoring, parameters and execution. Not needed until #13. |
| Blueprint graph authoring | Covered | `BlueprintTools` | Create Blueprints, variables, functions, events and dispatchers; write whole graphs with `write_graph_dsl`; compile. Components are added with `ActorTools.add_component`. |
| Enhanced Input | Partly covered | `DataAssetTools`, `ObjectTools`, `BlueprintTools` | No dedicated tool. Input Actions and Mapping Contexts are data assets, so `DataAssetTools.create` plus `ObjectTools.set_properties` should author them. Fallback: editor Python. |
| Animation Blueprint | Partly covered | `BlueprintTools`, `SkeletalMeshTools`, `ControlRigTools` | Event graphs only; no tool edits an AnimGraph or state machine. Beacon reuses the template's `ABP_Unarmed`. Fallback: manual step. |
| NavMesh | Partly covered | `SceneTools`, `ObjectTools`, `ConfigSettingsToolset` | No dedicated tool. Place a `NavMeshBoundsVolume` with `add_to_scene_from_class` and scale it. Fallback for a rebuild: console command through the Slate inspector. |
| Behaviour Tree or StateTree | Not covered | `BehaviorTreeTools`, `StateTreeTools` (both inspect only) | Neither toolset can create an asset or add a node. Fallback: editor Python, which in 5.8 exposes `BehaviorTree.root_node` and `BTCompositeNode.children`. Task logic stays in Blueprint task classes made with `BlueprintTools`. |
| EQS | Not covered | none | No EQS tool. `EnvQuery` is a data asset, so the asset can be created with `DataAssetTools.create`, but generators and tests are not exposed. Fallback: editor Python; if that cannot build the query options, a Blueprint generator class. |
| DataTables and DataAssets | Partly covered | `DataTableTools`, `DataAssetTools`, `ObjectTools`, `CurveTableTools` | Tables, rows and data asset instances are covered. There is no tool to create a row struct, and `DataTableTools.create` needs one. Beacon uses data assets whose class is a Blueprint made with `BlueprintTools`. |
| UMG | Covered | `UMGToolSet`, `ObjectTools`, `BlueprintTools` | Widget Blueprints, widget trees, event binding and compile. Widget properties go through `ObjectTools`. |
| Materials | Covered | `MaterialTools`, `MaterialInstanceTools` | Material graphs and material instances. |
| Niagara | Covered | `NiagaraToolset_System`, `NiagaraToolset_Component`, `NiagaraToolset_Blueprint`, `NiagaraToolset_Assets`, `NiagaraToolset_Info` | Systems, emitters, modules and component overrides. Not needed until #12. |
| Audio | Not covered | none | No tool imports or authors sounds. Blueprint graphs can play existing engine sounds. Fallback: editor Python for import. |
| Lighting | Partly covered | `SceneTools`, `ObjectTools` | No dedicated tool. Lights are actors: place them with `SceneTools` and set their component properties with `ObjectTools`. |
| Sequencer | Covered | `SequencerTools`, `SequencerKeyframingTools`, and five more Sequencer toolsets | Sequences, bindings, tracks and keys. Not needed until #14. |
| SaveGame | Partly covered | `BlueprintTools` | No dedicated tool. A SaveGame class and the save and load graphs are ordinary Blueprint work. |
| PIE control | Covered | `EditorAppToolset` | `StartPIE`, `StopPIE`, `IsPIERunning`. There is no input tool; drive the game with console commands through the Slate inspector. |
| Log reading | Covered | `LogsToolset` | `GetLogEntries` filters by category and regular expression. |
| Viewport screenshots | Covered | `EditorAppToolset`, `SlateInspectorToolset` | `CaptureViewport` for the level viewport, `CaptureEditorImage` and `Screenshot` for editor UI. |
| Custom C++ tools | Partly covered | `PluginToolset`, `AssetTools` | `PluginToolset.CreatePlugin` scaffolds a plugin and `AssetTools.write_file` writes source, but nothing compiles it, and new tools need an editor restart. Fallback: build from the command line. |
| Packaging | Not covered | none | No build or packaging tool. Fallback: run the engine's `RunUAT BuildCookRun` from a shell. |

## Tickets affected by a gap

| Ticket | Gap | Fallback |
|---|---|---|
| #4 | No tool creates a level, and there is no landscape tool. | Duplicate the template level; build the island from primitives. |
| #5 | Behaviour Tree and StateTree tools are inspect only. | Build the tree with editor Python; write task logic as Blueprint task classes. |
| #8 | No tool creates a DataTable row struct. | Use data assets with a Blueprint-defined class. |
| #9 | No EQS tool. | Editor Python; otherwise a Blueprint generator. |
| #18 | No packaging tool. | `RunUAT BuildCookRun` from a shell. |

## Where building Beacon changed the picture

The map above was written before anything was built. These are the places where tickets #4 to #10 proved it wrong or incomplete; the finding has the detail.

| Feature area | What turned out | Finding |
|---|---|---|
| Level and actor editing | Saving is the weak point: `save_assets` on a map skips changed actors unless the map file itself is dirty, and `set_actor_transform` resets a scale it was not given. Collision settings cannot be changed with `ObjectTools`. | F-008, F-009, F-015 |
| Blueprint graph authoring | Works for almost everything through the graph DSL. It cannot write Enhanced Input action events, drops positional arguments to a Blueprint's own functions, and `read_graph_dsl` marks the Blueprint dirty. | F-012, F-018, F-022, F-024, F-025, F-029 |
| Enhanced Input | Covered in practice by `DataAssetTools` and `ObjectTools`, apart from triggers and modifiers. | F-021 |
| NavMesh | Covered in practice by scene and settings tools plus one console command. | F-016 |
| Behaviour Tree | Editor Python can build a whole tree; the MCP's inspect tools then confirm it. | F-017 |
| EQS | No scripted route at all. Needs a person or C++. | F-030 |
| DataTables and DataAssets | Data assets with Blueprint-defined classes cover the need; DataTables stay out of reach without a row struct. | F-028 |
| UMG | Covered, including layout and fonts through `ObjectTools`. | F-019 |
| PIE control, screenshots | PIE start and stop are tools. Input, game state and a picture of the running game all need workarounds. | F-013, F-014, F-027 |
