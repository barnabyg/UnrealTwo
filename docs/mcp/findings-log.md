# Unreal MCP findings log

What happened each time Beacon was built through the UE 5.8 Unreal MCP: which tool was used, whether it worked, and what was used instead when it did not. Every ticket appends entries here. The tool names refer to [tool-inventory.md](tool-inventory.md); the planned coverage is in [capability-map.md](capability-map.md).

## Entry format

Add entries at the end, numbered in order. Do not rewrite an old entry when something changes later; add a new one that refers to it.

```markdown
### F-000: one-line summary

- **Ticket:** #n (the ticket the finding belongs to; say in the notes if it was found during a later one)
- **Capability:** the feature area from the capability map, or "agent workflow" for a finding about driving the MCP itself
- **Tool used:** `Toolset.tool`, or "none" when no tool exists
- **Outcome:** worked | worked with a workaround | failed | no tool
- **Fallback used:** none | editor Python | C++ | manual step | other MCP tool (say which) | script client (`Tools/mcp/beacon_mcp.py`)
- **Notes:** what a later ticket needs to know: exact arguments that mattered, error text, how the fallback was run
```

**Outcome** values mean:

- **worked**: the tool did the job as documented.
- **worked with a workaround**: the tool did the job only after an extra step that its description does not mention.
- **failed**: the tool exists and errored or did the wrong thing.
- **no tool**: the server has nothing for this job.

## Entries

### F-001: create, read back and delete an actor

- **Ticket:** #3
- **Capability:** level and actor editing
- **Tool used:** `SceneTools.add_to_scene_from_asset`, `SceneTools.find_actors`, `ActorTools.get_actor_transform`, `SceneTools.remove_from_scene`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** Placed `/Engine/BasicShapes/Cube` as `SmokeTestCube` at (0, 0, 500), yaw 45, scale 2 in a scratch level. `find_actors` found it by label, the transform read back exactly (yaw came back as 45.000000000000028), `remove_from_scene` returned true and a second `find_actors` returned an empty list. `find_actors` requires `name`, `tag` and `collision_channels` even when unused; pass `""`, `""` and `[]`.

### F-002: there is no tool that creates a level

- **Ticket:** #3
- **Capability:** level and actor editing
- **Tool used:** none for creation; `AssetTools.duplicate`, `AssetTools.save_assets`, `SceneTools.load_level`
- **Outcome:** no tool
- **Fallback used:** other MCP tool: duplicate the template level
- **Notes:** `AssetTools.duplicate` on `/Game/ThirdPerson/Lvl_ThirdPerson` copies the map and its external actor files. The copy is unsaved, and `load_level` refuses it with "the level has unsaved changes. Save the level before loading it." Call `save_assets` on the new map first. `AssetTools.delete` on the folder removed the scratch map and its external actors, but left an empty `Content/__ExternalActors__/Scratch` directory on disk.

### F-003: there is no tool for console commands or editor Python

- **Ticket:** #3
- **Capability:** agent workflow
- **Tool used:** none directly; `SlateInspectorToolset.Snapshot`, `Click`, `Type`
- **Outcome:** no tool
- **Fallback used:** other MCP tool: type into the editor's `Cmd` box through the Slate inspector
- **Notes:** `EditorAppToolset` can only search console variables, and `ProgrammaticToolset.execute_tool_script` is a sandbox that can call other tools but imports only `json`, `math`, `datetime`, `copy`, `re` and `time`. Console commands do work through UI automation: take a `Snapshot`, find the `textbox` that follows `text "Cmd"` in the status bar, `Click` it, then `Type` with `submit: true`. `Type` returns false and does nothing if the box was not clicked first. `py <statement>` and `py "<file>"` both run, which is how every "editor Python" fallback in this log is executed. `Tools/mcp/beacon_mcp.py console` and `py` wrap these steps.

### F-004: opening a duplicated level raises the Message Log window

- **Ticket:** #3
- **Capability:** level and actor editing
- **Tool used:** `SceneTools.load_level`, `SlateInspectorToolset.Windows`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** After duplicating and loading a level the editor opened a floating Message Log window (Asset Check and Map Check each had one entry). While it had focus, `SlateInspectorToolset.Type` on the main window's console box returned false. `Windows` with `action: "close"` and the window's index closed it.

### F-005: large results do not fit in an agent's context

- **Ticket:** #3
- **Capability:** log reading, viewport screenshots
- **Tool used:** `describe_toolset`, `SceneTools.find_actors`, `EditorAppToolset.CaptureViewport`
- **Outcome:** worked with a workaround
- **Fallback used:** script client (`Tools/mcp/beacon_mcp.py`)
- **Notes:** `describe_toolset` for `BlueprintTools` is 72,000 characters, and `find_actors` with no filter lists every actor in the level. Images come back as base64 inside the JSON result. `Tools/mcp/beacon_mcp.py` calls the same `call_tool` endpoint and can print compact signatures (`describe`), save a capture to a PNG (`call ... --png`), and filter log lines (`logs`).

### F-006: the island level is built from primitives and material instances

- **Ticket:** #4
- **Capability:** level and actor editing, materials
- **Tool used:** `SceneTools.add_to_scene_from_asset`, `SceneTools.set_actor_folder`, `ActorTools.get_components`, `ObjectTools.set_properties`, `MaterialInstanceTools.create`, `set_vector_parameter`, `set_scalar_parameter`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** Ground, beach, seabed, sea and rocks are scaled `/Engine/BasicShapes` meshes. A mesh gets its material by setting `overrideMaterials` on its StaticMeshComponent. Property names are lowerCamelCase in results but are matched without regard to case when set. An object reference must be the full `Package.Object` path (`/Game/Beacon/Materials/MI_Sea.MI_Sea`); the package path alone fails with "is not a valid object path for property". Asset paths for `add_to_scene_from_asset`, `save_assets` and `exists` are the package path alone.

### F-007: PrimitiveTools and child Blueprints work on Blueprint assets

- **Ticket:** #4
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.create`, `get_default_object`, `compile_blueprint`, `PrimitiveTools.add_cylinder`, `add_cone`, `add_cube`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** `BlueprintTools.create` takes the parent class as `asset_type`. Passing another Blueprint's generated class (`..._C`) makes a child Blueprint. Passing the Blueprint's class default object to `PrimitiveTools` adds the shape as a component template named `<Name>_GEN_VARIABLE`, which then takes `ObjectTools.set_properties`. Class defaults such as `defaultPawnClass` are set on `Default__<Name>_C`.

### F-008: collision settings cannot be changed through ObjectTools

- **Ticket:** #4
- **Capability:** level and actor editing
- **Tool used:** `ObjectTools.set_properties` on `bodyInstance`
- **Outcome:** failed
- **Fallback used:** other MCP tool: `StaticMeshTools.remove_collisions` on a copy of the mesh, and a Blueprint graph for per-channel responses
- **Notes:** Setting `bodyInstance.collisionEnabled` to `NoCollision` returns true and leaves the value at `QueryAndPhysics`. Setting `collisionProfileName` is stored but not applied, even after reloading the level. For the sea, `AssetTools.duplicate` copied the engine plane to `/Game/Beacon/Meshes/SM_SeaPlane` and `remove_collisions` stripped its simple collision, so the player walks through it. `SceneTools.trace_world` still hits that mesh, so it traces complex collision and cannot confirm this; the PIE walk test did. The boundary walls needed to block pawns but not the camera, which `BP_BoundaryWall` does in its BeginPlay graph with `SetCollisionResponseToChannel`.

### F-009: set_actor_transform resets the scale when the scale is left out

- **Ticket:** #4
- **Capability:** level and actor editing
- **Tool used:** `ActorTools.set_actor_transform`
- **Outcome:** failed
- **Fallback used:** none: always pass location, rotation and scale
- **Notes:** The transform type's description says unset fields mean "don't change". Moving the seabed with only `location` reset its scale from (92, 92, 1) to (1, 1, 1), and the player fell out of the world on the next PIE run. Read the transform first and send all three parts back.

### F-010: save_actor fails on actors of a level that stores one file per actor

- **Ticket:** #4
- **Capability:** level and actor editing
- **Tool used:** `SceneTools.save_actor`, `AssetTools.save_assets`
- **Outcome:** failed
- **Fallback used:** other MCP tool: `AssetTools.save_assets` on the map
- **Notes:** `save_actor` on a newly placed actor failed with "Asset does not exist: /Game/__ExternalActors__/Beacon/Maps/Lvl_Island/3/T7/..." and "Failed to save 'Sea'". `save_assets` with the map's package path saves the map and every changed external actor file.

### F-011: project settings are written through ConfigSettingsToolset

- **Ticket:** #4
- **Capability:** level and actor editing
- **Tool used:** `ConfigSettingsToolset.SetSectionProperties`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** Container `Project`, category `Project`, section `Maps`, with `GameDefaultMap`, `EditorStartupMap` and `GlobalDefaultGameMode` given as `{"refPath": ...}` objects. The tool wrote `Config/DefaultEngine.ini` at once.

### F-012: Blueprint graphs are written with the graph DSL

- **Ticket:** #4
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.get_graph`, `find_node_types`, `get_node_type_pins`, `write_graph_dsl`, `read_graph_dsl`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** `find_node_types` gives the type id (`Collision|SetCollisionResponsetoChannel`); a component is read with `Variables|Default|Get<ComponentName>`; enum pins take the value name as a quoted string (`"ECC_Camera"`). `read_graph_dsl` leaves out arguments that equal the pin's default, so a missing argument in the read-back is not an error.

### F-013: PIE is controlled by tools, and the game is driven by console commands

- **Ticket:** #4
- **Capability:** PIE control, log reading
- **Tool used:** `EditorAppToolset.StartPIE`, `StopPIE`, `LogsToolset.GetLogEntries`, `SlateInspectorToolset.Type`
- **Outcome:** worked with a workaround
- **Fallback used:** editor Python, to read game state
- **Notes:** There is no tool for player input or for reading the PIE world. Typing `Input.+key W` and `Input.-key W` into the editor's `Cmd` box holds and releases a key in the running game. `Tools/editor_python/pie_state.py` reads the player pawn through `UnrealEditorSubsystem.get_game_world()` and prints it as a log line. Measured on the island: 1.5 s of W moved the player from x = -1500 to x = -385 (stopped by the lighthouse base), SpaceBar put the player in the air, `Gamepad_RightX` turned the camera 10 degrees, and 11 s of S ended at x = -4240 against the boundary wall. The full procedure is in `docs/agents/verify-loop.md`.

### F-014: CaptureViewport cannot show the running game

- **Ticket:** #4
- **Capability:** viewport screenshots
- **Tool used:** `EditorAppToolset.CaptureViewport`, `SlateInspectorToolset.Screenshot`
- **Outcome:** worked with a workaround
- **Fallback used:** other MCP tool: `SlateInspectorToolset.Screenshot` on the viewport panel
- **Notes:** `CaptureViewport` fails without `captureTransform` and without `annotations` ("input param ... needs a default value"), although the schema marks both optional. With both supplied during PIE it renders the editor world from the game camera's position: the player is missing, and editor-only icons and hidden-in-game actors are drawn. `Screenshot` on the viewport's splitter panel returns the pixels on screen, which is the game.

### F-015: save_assets on a map skips changed actors unless the map file is dirty

- **Ticket:** #4
- **Capability:** level and actor editing
- **Tool used:** `AssetTools.save_assets`, `SceneTools.save_actor`
- **Outcome:** failed
- **Fallback used:** editor Python: `Tools/editor_python/save_dirty.py`, run with `beacon_mcp.py save`
- **Notes:** Found during #5. This corrects F-010. In a level that stores one file per actor, `save_assets` on the map saved the actor files only while the map package itself was dirty (in #4, right after a WorldSettings change). Later actor edits left the map package clean; `save_assets` then returned true and wrote nothing, and `is_dirty` on the map said false, while 54 actor packages were unsaved. The boundary wall swap and the seabed fix from #4 were committed unsaved for that reason. `save_assets` and `save_actor` on the actor packages both fail with "Asset does not exist". The script calls `EditorLoadingAndSavingUtils.save_dirty_packages` and reports the unsaved count before and after. Check `git status` after saving a level.

### F-016: the NavMesh is set up with generic scene and settings tools

- **Ticket:** #5
- **Capability:** NavMesh
- **Tool used:** `SceneTools.add_to_scene_from_class`, `ActorTools.set_actor_transform`, `ConfigSettingsToolset.SetSectionProperties`, `ObjectTools.set_properties`
- **Outcome:** worked with a workaround
- **Fallback used:** other MCP tool: the console command `RebuildNavigation` through the Slate inspector
- **Notes:** Placing `/Script/NavigationSystem.NavMeshBoundsVolume` gives a 200 cm cube brush; scaling the actor to (40, 40, 8) covers the island, and the editor creates the `RecastNavMesh` actor by itself. Runtime generation was set to `Dynamic` in project settings (section `NavigationMesh`) and again on the existing `RecastNavMesh` actor, which keeps the value it was created with. PIE then warned "Recreating dtNavMesh instance ... due mismatch in number of bytes required to store serialized maxTiles" until `RebuildNavigation` was run and the level saved. A path query from behind a rock returned a three-point path around its corner (2357 cm against 2328 cm straight).

### F-017: the Behaviour Tree is built with editor Python

- **Ticket:** #5
- **Capability:** Behaviour Tree or StateTree
- **Tool used:** none for authoring; `BehaviorTreeTools.list_nodes`, `get_node_depths`, `get_blackboard` to check the result
- **Outcome:** no tool
- **Fallback used:** editor Python: `Tools/editor_python/build_creature_ai.py`
- **Notes:** The script creates `BB_Creature` and `BT_Creature` with their factories, makes node objects with `unreal.new_object(..., outer=tree)` and wires them through `BTCompositeNode.children` and `BehaviorTree.root_node`, which 5.8 exposes. Three things were not obvious. The Blackboard key type classes are not Python names and are loaded with `unreal.load_class(None, "/Script/AIModule.BlackboardKeyType_Vector")`. `BTTask_MoveTo.acceptable_radius` is a `ValueOrBBKey_Float` struct, so its `default_value` is set instead of assigning a float. Nodes are reached with `set_editor_property` even though `dir()` lists only `node_name`. The tree has no editor graph when written; opening it in the Behaviour Tree editor rebuilt the graph from the asset, kept all four nodes, and marked the asset dirty. The tree ran in PIE unchanged.

### F-018: lessons from writing gameplay graphs with the DSL

- **Ticket:** #5
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.add_event`, `add_function_graph`, `add_variable`, `add_object_variable`, `write_graph_dsl`, `read_graph_dsl`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** An event's DSL name is not its function name: `ReceiveExecuteAI` is `AI|EventReceiveExecuteAI`, `ReceiveAnyDamage` is `Game|Damage|EventAnyDamage`, and a custom event is `Custom|<Name>`. Create the node with `add_event`, then `read_graph_dsl` to see the name. Writing an event again replaces its old chain. A `Name (by ref)` pin rejects a literal ("Could not set value ... on pin KeyName"); feed it from `Utilities|Name|MakeLiteralName`. Another Blueprint's variable is `Class|BPCreature|GetHealth`, with the underscore of `BP_Creature` dropped; a Blueprint's own function is `CallFunction|<Name>`. A `bind` of a pure expression is not a stored value: every node that reads it evaluates it again. Binding `health - damage`, setting the health, then comparing the bound value subtracted the damage twice, so read the variable again after setting it.

### F-019: the HUD is a Widget Blueprint; on-screen debug text did not show

- **Ticket:** #5
- **Capability:** UMG
- **Tool used:** `UMGToolSet.CreateWidgetBlueprint`, `AddWidget`, `RenameWidget`, `ToggleWidgetAsVariable`, `CompileWidgetBlueprint`, `ObjectTools.list_properties`, `set_properties`, `BlueprintTools.write_graph_dsl`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** `Development|PrintString` with `bPrintToScreen` wrote to the log but drew nothing in the PIE viewport, so the lighthouse health and the game-over message moved to `WBP_BeaconHUD`. Text blocks sit on a canvas panel; anchors, offsets and auto-size are the slot's `layoutData`, and font size and colour are the text block's `font` and `colorAndOpacity`, all set with `ObjectTools`. A text block must be toggled to a variable before the graph can read it as `Variables|WBP_BeaconHUD|Get<Name>`. The HUD's tick graph reads the lighthouse and the game mode each frame.

### F-020: one project setting removes an AI warning at the end of every PIE run

- **Ticket:** #5
- **Capability:** NavMesh
- **Tool used:** `ConfigSettingsToolset.SetSectionProperties`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** Once an AI controller existed, stopping PIE logged "LogCrowdFollowing: Warning: Unable to find RecastNavMesh instance while trying to create UCrowdManager instance". Beacon does not use crowd following, so `crowdManagerClass` in section `NavigationSystem` was set to null, which writes `CrowdManagerClass=None`.

### F-021: Enhanced Input assets are authored as plain data assets

- **Ticket:** #6
- **Capability:** Enhanced Input
- **Tool used:** `DataAssetTools.create`, `ObjectTools.get_properties`, `set_properties`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** `DataAssetTools.create` with `/Script/EnhancedInput.InputAction` and `/Script/EnhancedInput.InputMappingContext` made `IA_Fire` and `IMC_Beacon`. In 5.8 a mapping context keeps its keys in `defaultKeyMappings.mappings`, not `mappings`; each entry is `{"action": {"refPath": ...}, "key": "LeftMouseButton", "triggers": [], "modifiers": []}`. Triggers and modifiers are instanced objects and were left empty, so the action fires every frame while held and the Fire function applies its own cooldown. Beacon's context is added by `BP_BeaconCharacter` a tick after BeginPlay, the way the template controller adds its own.

### F-022: the graph DSL cannot write Enhanced Input action events

- **Ticket:** #6
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.write_graph_dsl`, `create_node`, `get_node_infos`, `connect_pins`
- **Outcome:** worked with a workaround
- **Fallback used:** other MCP tool: `create_node` and `connect_pins`
- **Notes:** `(event Input|EnhancedActionEvents|IA_Fire ...)` and `(event EnhancedInputActionIA_Fire ...)` both fail with "AddEvent|... does not exist", even when the node is already in the graph. `read_graph_dsl` prints these events with an empty body, because their exec outputs are named (Triggered, Started, Ongoing, Canceled, Completed) and are dropped. The event was made with `create_node` (type id `Input|EnhancedActionEvents|IA_Fire`), a `CallFunction|Fire` node was made the same way, and `connect_pins` joined the event's `Triggered` pin to it, using the `pin_id` values from `get_node_infos`. The logic itself lives in a function graph, which the DSL writes without trouble. To check which output of a multi-output node the DSL wired (for example `Collision|BreakHitResult`), read `connected_pins` from `get_node_infos`; the DSL read-back does not say.

### F-023: properties set on an inherited component of a child Blueprint do not reach the game

- **Ticket:** #6
- **Capability:** Blueprint graph authoring
- **Tool used:** `ActorTools.get_components`, `ObjectTools.set_properties`
- **Outcome:** failed
- **Fallback used:** other MCP tool: a BeginPlay graph
- **Notes:** `BP_BeaconCharacter` inherits its camera boom from the template character. `get_components` on the child's class default object returns the boom, and setting `socketOffset` on it returned true and read back correctly, but the camera did not move in PIE. Components a Blueprint adds itself (F-007) do keep their properties. The offset is now set in BeginPlay with `Class|SpringArmComponent|SetSocketOffset`.

### F-024: read_graph_dsl marks the Blueprint it reads as unsaved

- **Ticket:** #6
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.read_graph_dsl`
- **Outcome:** worked with a workaround
- **Fallback used:** editor Python: `save_dirty.py` saves only packages under `/Game/Beacon`
- **Notes:** Reading the template controller's graph to learn how it adds mapping contexts left `/Game/ThirdPerson/Blueprints/BP_ThirdPersonPlayerController` dirty. `list_variables` and `get_graph` did not; `read_graph_dsl` did, on every call. The next save-everything rewrote two template Blueprints that nobody had changed. `save_dirty.py` now skips packages outside Beacon's own content and lists what it skipped.

### F-025: DSL calls can drop arguments or pick the wrong overload without an error

- **Ticket:** #7
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.write_graph_dsl`, `get_node_infos`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** `(CallFunction|Notify "Turret placed")` compiled, but the `Message` pin stayed empty and every notice in the game was blank. A positional argument to a Blueprint's own function is not applied; `(CallFunction|Notify :Message "Turret placed")` is. Two nodes share the id `Pawn|GetControlRotation`; the DSL picked the Controller's, and the Blueprint failed to compile with "This blueprint (self) is not a Controller". Passing `:self (Pawn|GetController)` made that choice valid. After writing a graph, read each call's pin values with `get_node_infos` rather than trusting the DSL read-back.

### F-026: components are parented with set_parent_component, in the parent's scaled space

- **Ticket:** #7
- **Capability:** Blueprint graph authoring
- **Tool used:** `PrimitiveTools.add_sphere`, `add_cube`, `ActorTools.set_parent_component`, `ObjectTools.set_properties`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** The turret's barrel is a child of its head so that turning the head turns both. `set_parent_component` works on Blueprint component templates. The child keeps its numbers but they now mean "relative to the parent", and a primitive's size is its scale: under a sphere of radius 32 (scale 0.64) the barrel's offset and scale had to be divided by 0.64.

### F-027: slow motion makes short events capturable

- **Ticket:** #7
- **Capability:** PIE control, viewport screenshots
- **Tool used:** `SlateInspectorToolset.Type` (console), `SlateInspectorToolset.Screenshot`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** A turret kills a creature in 2.5 s of game time. With the editor in the background at about 3 frames a second, each tool call costs a noticeable slice of that, and three attempts to capture the turret firing missed. Typing `slomo 0.15` into the `Cmd` box after the setup stretched the engagement enough to read the state and take the screenshot; `slomo 1` restores normal speed. Positioning the player for a test is done with a few lines of editor Python that move the pawn and set the control rotation.

### F-028: waves and turret types are data assets with Blueprint-defined classes

- **Ticket:** #8
- **Capability:** DataTables and DataAssets
- **Tool used:** `BlueprintTools.create`, `add_variable`, `add_object_variable`, `DataAssetTools.create`, `ObjectTools.set_properties`
- **Outcome:** worked with a workaround
- **Fallback used:** other MCP tool: data assets instead of a DataTable
- **Notes:** A DataTable needs a row struct and no tool creates one, so the data lives in data assets. `BlueprintTools.create` with parent `/Script/Engine.PrimaryDataAsset` makes the class (`BP_WaveData`, `BP_NightData`, `BP_TurretType`, `BP_CreatureType`); its variables are the columns. `add_object_variable` with `container_type: "ARRAY"` gives a list of references to other data assets, which is how a night lists its waves and a wave lists its creature types. `DataAssetTools.create` takes the Blueprint's generated class (`..._C`) and `set_properties` fills an instance in one call, including arrays of `{"refPath": ...}`. Changing `Count` on `DA_Wave_N1_1` from 3 to 1 with `set_properties` changed the next PIE run from three creatures in wave one to one, with no graph touched.

### F-029: more DSL details found while writing the wave director

- **Ticket:** #8
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.add_function_graph`, `add_function_param`, `add_object_function_param`, `write_graph_dsl`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** A function's parameters must exist before its body is written; `(fn ApplyType (Type) ...)` on a graph without the parameter fails with "Function parameter(s) not found in graph". The `%` operator has no integer form ("Utilities|Operators|Modulo does not exist"); use `Math|Integer|%(Integer)`. An array element is `Utilities|Array|Get(acopy)`. The same member has different ids from inside and outside its class: `Variables|Character|GetCharacterMovement` in the character's own graph, `Class|Character|GetCharacterMovement` elsewhere. `Rendering|Material|SetVectorParameterValue` resolved to the material parameter collection node, not the dynamic material one; `Rendering|Material|SetVectorParameterValueonMaterials` on the mesh component colours a mesh without that ambiguity. Latent `Delay` nodes work in event chains written by the DSL, including an event that calls itself after the delay, which is how waves are paced.

### F-030: an EQS query cannot be authored by any scripted route

- **Ticket:** #9
- **Capability:** EQS
- **Tool used:** none exists; tried `DataAssetTools`-style creation, `ObjectTools.set_properties`, editor Python, the console and `SlateInspectorToolset`
- **Outcome:** no tool
- **Fallback used:** manual step, still to be done by a person (see notes)
- **Notes:** The asset and its parts can be created: an `EnvQuery` with `DataAssetFactory`, and option, generator and test objects with `unreal.new_object` on classes loaded by path. `ObjectTools` then reads and sets the generator's and the test's own settings (`searchedActorClass`, `searchRadius`, `scoringEquation`, `testPurpose`). What cannot be done is joining them. `EnvQuery.Options`, `EnvQueryOption.Generator` and `EnvQueryOption.Tests` are protected: Python answers "is protected and cannot be set", and `ObjectTools.set_properties` answers "the following properties could not be set". The console `set` command answers "Set commands not allowed in the editor". No engine or plugin content contains an `EnvQuery` asset to duplicate. In the EQS graph editor, the Slate inspector exposes the root node's title but not the graph panel or any pin: dragging from the node moved the node, and a right-click found no surface that opens the node menu. `BlueprintTools.create_node` only knows Blueprint node types. A Blueprint generator class (`EnvQueryGenerator_BlueprintBase`), the fallback first proposed on the ticket, does not help: it too only runs from an option inside a query asset, which is the link that cannot be made. What remains is a person adding the generator and test in the EQS editor (about two minutes), or a C++ editor function, which would end Beacon being a Blueprint-only project. Until then the turret-hunter picks its target in a Blueprint task (`BTTask_FindTurret`).

### F-031: creature variants reuse the data, graph and tree routes already found

- **Ticket:** #9
- **Capability:** Behaviour Tree or StateTree, DataTables and DataAssets
- **Tool used:** `DataAssetTools.create`, `ObjectTools.set_properties`, `BlueprintTools.write_graph_dsl`; editor Python for the tree
- **Outcome:** worked with a workaround
- **Fallback used:** editor Python: `Tools/editor_python/build_creature_ai.py`
- **Notes:** A Runner and a Hunter are two more `BP_CreatureType` data assets; one `BP_Creature` class takes speed, health, scale, colour and tree from the asset. The Hunter's tree is a Selector over two plans, "hunt turret" then "attack lighthouse", so it falls back when no turret stands or its turret dies. The build script makes both trees from a table of plans. Measured in PIE: the Hunter closed on the island at about 159 cm/s and the Shambler at about 257 cm/s; the Hunter walked to a turret on the far side from where it landed, took it from 60 health to destroyed, then went for the lighthouse. Creatures for a test are spawned by calling the game mode's `SpawnCreature` from editor Python with `call_method`. Rebuilding a tree leaves any editor graph from an earlier look at the asset out of date; delete the asset first if its structure changes.

### F-032: the day/night loop is Blueprint graphs over data, with lights driven from nodes

- **Ticket:** #10
- **Capability:** lighting, Blueprint graph authoring, Enhanced Input
- **Tool used:** `BlueprintTools.write_graph_dsl`, `ActorTools.add_component`, `ObjectTools.set_properties`, `DataAssetTools.create`, `UMGToolSet.AddWidget`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** The game mode holds the phase, the night number, the resources and a list of night data assets. Lighting is switched from a graph: the level's directional light and sky light are found with `Actor|GetActorOfClass`, their components with `Actor|GetComponentbyClass` plus a cast, and intensity and colour set with `Rendering|Components|Light|SetIntensity` and `SetLightColor`. The lighthouse beam is a `SpotLightComponent` added to the Blueprint with `ActorTools.add_component`, shown at night and turned each tick with `Transformation|AddWorldRotation`. A function named `SetBeam` clashed with the setter of the component variable `Beam` (two nodes with the id `Class|BPLighthouse|SetBeam`), so it is called `SwitchBeam`. A multi-exec call such as a cast or `Utilities|IsValid` ends the statement list it is in, so a function that needs two of them in a row calls two helper functions. Measured in PIE: eight pickups by day, +10 resources on walking over one, a Sentry for 25 and a Sniper for 40, a Sprayer refused at 15 resources, sun intensity 3.0 by day and 0.3 at night, the beam's yaw moving at night, +20 and a new day after the night's last creature died, and night two playing `DA_Night_2`.

### F-033: Blueprint component changes do not reach an actor already placed in the level

- **Ticket:** #10
- **Capability:** level and actor editing
- **Tool used:** `ObjectTools.set_properties`, `reset_properties`, `SceneTools.remove_from_scene`, `add_to_scene_from_asset`
- **Outcome:** failed
- **Fallback used:** other MCP tool: delete the placed actor and place it again
- **Notes:** The beam was added to `BP_Lighthouse` while a lighthouse already stood in the level, and its settings were written to the component template afterwards. The template read back correctly, but the placed lighthouse kept the engine defaults (intensity 5000, radius 1000, at the actor's origin) in the editor and in PIE, so the night had no visible beam. On the placed actor's component, `reset_properties` returned to those class defaults rather than the Blueprint's values, and `set_properties` returned true and changed nothing. Removing the actor and placing the Blueprint again gave an instance with the template's values. Set a component's properties before any instance of the Blueprint is placed, or re-place the instances after.

### F-034: a hand-made EQS query is run from the tree and checked through the MCP

- **Ticket:** #9
- **Capability:** EQS
- **Tool used:** `ObjectTools.get_properties`, `AssetTools.get_dependencies`, `BehaviorTreeTools.list_nodes`; editor Python for the tree
- **Outcome:** worked with a workaround
- **Fallback used:** manual step for the query, editor Python for the tree
- **Notes:** This closes the gap left by F-030. A person made `EQS_NearestTurret` in the EQS editor: generator Actors Of Class `BP_Turret` within 10000 cm of the querier, and a Distance test with purpose Score and the Inverse Linear equation, so the nearest turret scores highest. Once the asset exists its parts can be read through the MCP at `EQS_NearestTurret:EnvQueryOption_0.EnvQueryGenerator_ActorsOfClass_0` and `...EnvQueryTest_Distance_0`, which is how the settings were confirmed. `build_creature_ai.py` puts a `BTTask_RunEQSQuery` in the Hunter's tree: the query and `SINGLE_RESULT` run mode go into the task's `eqs_request` struct, and the result into the `TargetActor` blackboard key. A Blueprint task then turns that target into a point to walk to. With no turret standing the query fails and the Selector falls through to the lighthouse plan. In PIE the Hunter attacked the nearer of two turrets first, then the other. The Blueprint task that used to choose the turret, `BTTask_FindTurret`, is deleted.

### F-035: menus, buttons and a progress bar are built with the UMG toolset and the graph DSL

- **Ticket:** #11
- **Capability:** UMG
- **Tool used:** `UMGToolSet.CreateWidgetBlueprint`, `AddWidget`, `RemoveWidget`, `ToggleWidgetAsVariable`, `BindToEventProperty`, `CompileWidgetBlueprint`, `ObjectTools.set_properties`, `BlueprintTools.write_graph_dsl`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** `WBP_MainMenu`, `WBP_GameOver`, `WBP_BuildMenu` and `WBP_BuildEntry` are new, and `WBP_BeaconHUD` gained a `ProgressBar`. `BindToEventProperty` with `eventName: "OnClicked"`, the button's variable name and `propertyClass: /Script/UMG.Button` adds the click event; the DSL then writes its body as `(event OnClicked(PlayButton) ...)`, unlike Enhanced Input events (F-022). A widget that another widget creates is typed `UserWidget` at the `CreateWidget` output, so cast it before setting its variables. The build menu makes one `WBP_BuildEntry` per turret type in a `for` loop over the game mode's `TurretTypes` and adds each to a `VerticalBox` with `Widget|Panel|AddChild`. An entry disables its button with `Widget|SetIsEnabled` while the player's resources are below the type's cost; Slate draws a disabled button and its label dimmed with no further styling. Removing a text block that a graph still reads makes `CompileWidgetBlueprint` fail with "This blueprint (self) is not a TextBlock", and while the Widget Blueprint is in that state `find_node_types` on its graph lists only part of the other Blueprints' members. Rewrite the graph first.

### F-036: set_properties takes its values as a JSON string and says nothing when given an object

- **Ticket:** #11
- **Capability:** agent workflow
- **Tool used:** `ObjectTools.set_properties`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** The schema types `values` as a string. Sending a JSON object instead returns `false` for every call with no error text, and nothing is set. Encode the object first (`json.dumps`). A struct can be given in part: `{"font": {"size": 28}}` changes the size and keeps the typeface.

### F-037: the Slate inspector sees and clicks the game's own widgets during PIE

- **Ticket:** #11
- **Capability:** PIE control
- **Tool used:** `SlateInspectorToolset.Snapshot`, `Click`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** UMG widgets are Slate widgets, so a snapshot taken while PIE runs lists them: `button "Play" [pos=655,605 size=280,72] [ref=b250]`, each text block with its current text, and `progressbar`. `Click` on a button's ref presses it in the game, which is how the menu, the build menu and the restart were tested without a person. A disabled button is marked `[disabled]`; `Click` on it still returns true and does nothing. Refs change whenever a widget is rebuilt, so take a new snapshot before each click. `beacon_mcp.py click "<label>"` wraps this, and `verify` now clicks Play because the game opens on its menu. The HUD's live values are read the same way, from the snapshot's text lines.

### F-038: two names the engine already uses broke the restart

- **Ticket:** #11
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.add_event`, `write_graph_dsl`
- **Outcome:** worked with a workaround
- **Fallback used:** none: different names
- **Notes:** A custom event named `RestartGame` on the game mode Blueprint was created without complaint, but `AGameMode` already has a function of that name. A call written from another Blueprint as `Class|BPBeaconGameMode|RestartGame` became the engine's `Game|RestartGame` node, and that Blueprint failed to compile with "Could not find a function named RestartGame in BP_BeaconGameMode_C". The event is `RestartRun`. Separately, the restart reopens the level with `Game|OpenLevel(byName)` and an option the game mode reads from `OptionsString` with `GameOptions|HasOption`. The option `restart` never arrived: the engine's travel code treats `?restart` as "reload the last URL" and the options string came back empty. The option is `SkipMenu`.

### F-039: more DSL details found while writing the menus

- **Ticket:** #11
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.write_graph_dsl`, `find_node_types`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** A boolean variable's node ids drop the `b` prefix: `bGameOver` is `Variables|Default|GetGameOver` inside its class and `Class|BPBeaconGameMode|GetGameOver` outside, although `read_graph_dsl` prints `(|GetbGameOver)`, which cannot be written back. A variable setter's pins are the value first and `self` second, so `(Class|WBPBuildEntry|SetTypeIndex entry i)` fails with "Could not connect pin"; write `:self entry :TypeIndex i`. `compile_blueprint` returns nothing on success.

### F-040: a Blueprint variable cannot be set from editor Python during PIE unless it is instance editable

- **Ticket:** #11
- **Capability:** agent workflow
- **Tool used:** none; editor Python through the console
- **Outcome:** no tool
- **Fallback used:** editor Python: call a Blueprint function instead
- **Notes:** `set_editor_property("Resources", 30)` on the running game mode raises "Property 'Resources' ... cannot be edited on instances". Reading works. To put the game in a state for a test, call one of the Blueprint's functions with `call_method("AddResources", args=(-30,))`, or apply damage with `GameplayStatics.apply_damage`.

### F-041: the hit flash is a material parameter, and reparenting a material instance does not mark it unsaved

- **Ticket:** #12
- **Capability:** materials
- **Tool used:** `MaterialTools.create_material`, `add_expression`, `connect_expressions`, `connect_to_output`, `recompile`, `MaterialInstanceTools.set_parent`, `list_parameters`, `ObjectTools.set_properties`
- **Outcome:** worked with a workaround
- **Fallback used:** editor Python, for one save
- **Notes:** `M_Creature` has a `Base Color` vector parameter, a `Flash` scalar (0 to 1), a `Flash Color` and a `Flash Glow`: base colour is a lerp from `Base Color` to `Flash Color` by `Flash`, and emissive is `Flash Color * Flash * Flash Glow`. Expression classes are `/Script/Engine.MaterialExpression<Name>`; a parameter's name and default are set with `ObjectTools` (`parameterName`, `defaultValue`), and a constant's value is its `r`. `MI_Creature` was reparented from the template's `M_FlatCol` and kept its `Base Color` override because the parameter name is the same. The creature sets `Flash` to 1 on damage with `Rendering|Material|SetScalarParameterValueonMaterials` and back to 0 after a `RetriggerableDelay` of 0.12 s. `set_parent` does not mark the instance's package dirty: `is_dirty` said false, `save_assets` returned true and wrote nothing, and `save_dirty.py` skipped it, while PIE showed the flash from the unsaved copy. `unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)` wrote it. Check `git status` for every asset a ticket changed, not only the ones it created.

### F-042: Niagara systems are made from engine templates and tuned through stack inputs

- **Ticket:** #12
- **Capability:** Niagara
- **Tool used:** `NiagaraToolset_System.CreateNiagaraSystem`, `GetSystemSummary`, `GetEmitterTopology`, `GetEmitterInputValues`, `RemoveEmitter`, `RemoveModule`, `SetStackInputData`, `GetSystemCompileState`, `GetStackIssues`
- **Outcome:** worked with a workaround
- **Fallback used:** script client (`Tools/mcp/beacon_mcp.py`), to read the large results
- **Notes:** A system needs a template. `NS_MuzzleFlash` comes from `/Niagara/DefaultAssets/Templates/Systems/DirectionalBurst` and `NS_DeathBurst` from `RadialBurst`; their ribbon emitters were removed with `RemoveEmitter`, and the module that fed the ribbon with `RemoveModule`. Every reference is the same struct: `system`, `emitterName`, `scriptName` (`EmitterUpdateScript`, `ParticleSpawnScript`, `ParticleUpdateScript`), `moduleName`, `rendererIndex` (-1 when unused) and `inputNameStack` (the input's name in a one-item list). A value is `{"struct": {"refPath": <type>}, "value": {...}}` with the type that `GetEmitterInputValues` reports: `/Script/Niagara.NiagaraInt32` and `NiagaraFloat` with `{"value": n}`, `/Script/CoreUObject.LinearColor`, `Vector2f` and `Vector3f` with their fields. Colour values above 1 make the sprites glow. Set this way: burst count, lifetime, sprite size, colour, cone axis and angle, gravity. Both systems compiled with no errors or warnings. `GetEmitterInputValues` for one template emitter is about 15,000 characters. The effects are spawned with `Niagara|SpawnSystematLocation`, which destroys the component when the system completes.

### F-043: no tool authors audio; the sounds are synthesised and imported with editor Python

- **Ticket:** #12
- **Capability:** audio
- **Tool used:** none exists
- **Outcome:** no tool
- **Fallback used:** editor Python: `Tools/editor_python/import_sfx.py`, after `Tools/audio/make_sfx.py`
- **Notes:** `make_sfx.py` writes three mono 16-bit 44.1 kHz WAV files from sine sweeps and seeded noise using only the Python standard library: a shot (0.14 s), a hit (0.09 s) and a death (0.45 s). `import_sfx.py` imports them with `AssetImportTask` (`automated`, `replace_existing`, `save`) into `/Game/Beacon/Audio`; the three `SoundWave` assets read back through `ObjectTools` with those durations, one channel and 44100 Hz. Graphs play them with `Audio|PlaySoundatLocation`, which takes the asset path as a quoted string. The agent cannot hear the game, so what is verified is that the assets exist, the nodes are wired and the log stays clean. A person should listen once.

### F-044: nodes in an existing graph can be swapped without rewriting the graph

- **Ticket:** #12
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.find_nodes`, `get_node_infos`, `create_node`, `connect_pins`, `delete_node`, `write_graph_dsl`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** The shot graphs read several outputs of `Collision|BreakHitResult`, which `read_graph_dsl` prints without saying which output is which (F-022), so writing the function again from its read-back was not safe. Each `DrawDebugLine` node was instead replaced in place: read its `connected_pins`, create a `CallFunction|ShotEffects` node, connect the same sources to `From`, `To` and `execute` and the same target to `then`, then delete the old node. `find_nodes` matches its `title` against the node's short title: `"Debug"` found the nodes, `"Draw Debug Line"` and `"Debug Line"` found none. Arithmetic on vectors reads back as `Math|Vector|vector*vector` but that id cannot be written ("does not exist"); write `(* vector 70.0)` and `(+ a b)`, which make the same nodes.

### F-045: frame rate and live effect counts are read with editor Python, with the background throttle switched off

- **Ticket:** #12
- **Capability:** PIE control
- **Tool used:** `ConfigSettingsToolset.GetSectionPropertyValues`, `SetSectionProperties`; editor Python
- **Outcome:** worked with a workaround
- **Fallback used:** editor Python
- **Notes:** No tool reports the frame rate. With the editor window in the background the editor runs at about 3 frames a second (see verify-loop.md), which hides any real cost. The setting is `bThrottleCPUWhenNotForeground` in container `Editor`, category `General`, section `EditorPerformanceSettings`. It was set to false for the measurement and back to true afterwards; it is a per-user preference and no tracked file changed. Frames per second is the change in `SystemLibrary.get_frame_count()` over the change in `GameplayStatics.get_real_time_seconds()` between two samples. Effects spawned at a location belong to the world settings actor, so `world.get_world_settings().get_components_by_class(unreal.NiagaraComponent)` lists the ones still alive. A dynamic material's parameter is read with `get_scalar_parameter_value("Flash")`.

### F-046: the scatter graph is built node by node with the PCG toolset

- **Ticket:** #13
- **Capability:** PCG
- **Tool used:** `PCGToolset.CreateGraph`, `ListNativeNodes`, `GetNativeNodeSchema`, `AddNode`, `UpdateNode`, `ConnectNodePins`, `DisconnectNodePins`, `GetNodeInfo`, `GetGraphStructure`, `ObjectTools.set_properties`
- **Outcome:** worked with a workaround
- **Fallback used:** other MCP tool: `ObjectTools`, for the mesh lists
- **Notes:** `PCG_IslandScatter` is World Ray Hit Query, Surface Sampler, a height filter, a radius filter, a Difference against actors tagged `ScatterExclude`, then two branches: rocks (Select Points, Bounds Modifier, a second Difference, Self Pruning, Transform Points, Static Mesh Spawner) and foliage (Difference against the rock points, Transform Points, Static Mesh Spawner). `AddNode` takes the node's settings as a JSON string. An attribute selector is a plain string: `"$Position.Z"` for a point property, `"Radius"` for an attribute. A range filter's threshold is `{"bUseConstantThreshold": true, "attributeTypes": {"type": "Double", "doubleValue": -5}}`. Distance from the lighthouse is `Attribute Vector Op` with `operation: "Length"` on `$Position`, written to `Radius`. `GetNativeNodeSchema` lists that node's inputs as `InA` and `InB`, but with a one-input operation the pin is `In`, and `ConnectNodePins` fails on `InA`. `ConnectNodePins` returns the conversion nodes it adds by itself (`ToPoint_0`, `FilterDataByType_0`). The spawner's mesh list is not a node parameter: it is `meshEntries` on the selector object that `GetNodeInfo` names (`...:SpawnRocks.PCGStaticMeshSpawnerSettings_1.DefaultSelectorInstance`), set with `ObjectTools`. Each entry's `descriptor` takes `staticMesh`, `overrideMaterials` and `bodyInstance.collisionProfileName`; here the collision profile is applied (rocks `BlockAll`, foliage `NoCollision`), unlike on a placed component (F-008).

### F-047: a graph instance is a PCG Volume, and its seed is a property of its PCG component

- **Ticket:** #13
- **Capability:** PCG
- **Tool used:** `PCGToolset.SpawnGraphInstance`, `ExecuteGraphInstance`, `ListGraphInstances`, `ActorTools.set_actor_transform`, `add_tag`, `ObjectTools.set_properties`
- **Outcome:** worked with a workaround
- **Fallback used:** editor Python, to read the result: `Tools/editor_python/scatter_state.py`
- **Notes:** `SpawnGraphInstance` places a PCG Volume with a 200 cm cube brush; scaling the actor to (30, 30, 4) covers the plateau, and the ray query and sampler work inside those bounds. The first `ExecuteGraphInstance` returned an empty issue list and the meshes appeared. The seed is `seed` on the component at `<volume path>.PCG Component`. Setting it with `ObjectTools` regenerates the scatter at once; an `ExecuteGraphInstance` straight after that fails with "Failed to call Execute on instance", and is not needed. No tool returns the generated instances, so `scatter_state.py` reads the volume's instanced mesh components and prints every instance position. Seed 42 gave the same sixteen rock positions twice; seed 7 shared none of them. The path from the west shore is a real actor, `Island_Path`, tagged `ScatterExclude`: the graph finds excluders by tag, so another clear area needs only a tagged actor. Subtracting the path after the rock footprint is set keeps a rock's body off the path: over eight seeds the nearest rock centre was 530 cm from the path's centre line, and the nearest foliage 252 cm, against a path half-width of 200 cm.

### F-048: the intro shot is authored with the Sequencer toolsets

- **Ticket:** #14
- **Capability:** Sequencer
- **Tool used:** `SceneTools.add_to_scene_from_class`, `SequencerTools.create_level_sequence`, `open_sequence`, `set_display_rate`, `set_playback_range`, `add_actors`, `get_tracks_on_binding`, `get_sections`, `set_section_range`, `set_section_completion_mode`, `SequencerKeyframingTools.get_channel_names`, `add_key_float`, `remove_key_at_frame`, `get_keys`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** `LS_IntroFlyover` is nine seconds at 30 frames a second and animates a `CineCameraActor` placed in the level as `IntroCamera`. The camera comes in from the east, passes round the south side of the lighthouse and ends behind the player in the west: about half a circle, not a full one. `add_actors` binds a level actor into the sequence that is open in the Sequencer editor, so call `open_sequence` first; it returns a binding (`bindingId` plus `sequence`) and gives a camera a transform track with one section. Channels are `Location.X/Y/Z`, `Rotation.X/Y/Z` and `Scale.X/Y/Z`, where rotation X is roll, Y is pitch and Z is yaw. Six keys per channel were added with `add_key_float` and `"cubic"` interpolation. Yaw is keyed as one falling run (-158 to -360) so the camera turns one way round the lighthouse instead of unwinding. `set_section_completion_mode` takes `"KeepState"`, which leaves the camera on its last key when the sequence ends. To change a key, remove it with `remove_key_at_frame` and add it again.

### F-049: Sequencer adds a Camera Cut track with a camera, and it fought the Blueprint for the view

- **Ticket:** #14
- **Capability:** Sequencer
- **Tool used:** `SequencerTools.add_actors`, `get_tracks_on_sequence`, `remove_track_from_sequence`
- **Outcome:** worked with a workaround
- **Fallback used:** none
- **Notes:** `add_actors` with a camera also adds a sequence-level `MovieSceneCameraCutTrack`, and its result does not mention it. The game mode sets the view itself: it cuts to `IntroCamera` when the shot starts and blends to the player with `Game|Player|SetViewTargetwithBlend` when it ends or is skipped. Watching the shot through worked. Skipping did not: the game mode started the blend and paused the sequence player, the pause evaluated the sequence once more, the cut track set the view back to the camera, and the game began with the view stuck over the sea. A per-frame trace (F-051) showed the view target go to the player and return to the camera one frame later. Removing the cut track with `remove_track_from_sequence` fixed it. If a sequence is meant to drive the view itself, keep the track and do not set the view target from a graph.

### F-050: binding a delegate needs node tools, and the skip key lives on the controller

- **Ticket:** #14
- **Capability:** Blueprint graph authoring, Enhanced Input
- **Tool used:** `BlueprintTools.create_node`, `connect_pins`, `list_compatible_event_functions`, `set_create_event_function`, `write_graph_dsl`, `DataAssetTools.create`
- **Outcome:** worked with a workaround
- **Fallback used:** other MCP tool: `create_node` and `connect_pins` instead of the DSL
- **Notes:** The game mode creates the player with `Sequencer|Player|CreateLevelSequencePlayer` (bind both outputs: `(bind (actor player) ...)`), calls `Play`, and binds the player's `OnFinished` to its `EndIntro` event. The bind node is `Sequencer|Player|BindEventtoOnFinished`. Four other classes have an `OnFinished` delegate under the id `EventDispatchers|BindEventtoOnFinished`; that id made a node for a gameplay task, and passing `declaring_class` for the sequence player failed with "does not exist". The delegate comes from an `EventDispatchers|CreateEvent` node whose function is chosen with `set_create_event_function`. `EndIntro` does nothing unless the shot is playing, so the finish and the skip can both call it. The pawn's input is disabled during the shot, which also silences the pawn's input events, so `IA_SkipIntro` is handled in `BP_BeaconPlayerController`. It is mapped to Enter and the gamepad's right face button; only Enter was tested. A one-line widget, `WBP_IntroHint`, shows "Enter: skip" during the shot. Space was not used: `IMC_Beacon` has a higher priority than the template's context, so mapping Space there would take it away from Jump.

### F-051: a per-frame trace in editor Python times short events

- **Ticket:** #14
- **Capability:** agent workflow
- **Tool used:** none; editor Python through the console
- **Outcome:** no tool
- **Fallback used:** editor Python
- **Notes:** Reading the game state through the console costs about three seconds a call, too slow to time a nine-second shot. A script registered `unreal.register_slate_post_tick_callback`, recorded the game time whenever the intro flag, the started flag or the view target changed, and sampled the camera once a second; a second script unregistered it and printed the rows. Keep the callback handle on the `unreal` module so the second script can find it. With the editor in the background the trace has one row every third of a second, which is the resolution of the times in the verification record.

### F-052: saving is a SaveGame Blueprint and ordinary graphs

- **Ticket:** #15
- **Capability:** SaveGame
- **Tool used:** `BlueprintTools.create`, `add_variable`, `add_object_variable`, `add_function_graph`, `add_function_param`, `write_graph_dsl`, `get_default_object`, `ObjectTools.set_properties`, `UMGToolSet.AddWidget`, `BindToEventProperty`
- **Outcome:** worked
- **Fallback used:** none
- **Notes:** `BP_BeaconSave` has the parent `/Script/Engine.SaveGame` and five variables: `SaveVersion`, `NightNumber`, `Resources`, and two arrays made with `container_type: "ARRAY"`, `TurretTypeNames` (string) and `TurretTransforms` (Transform). The game mode's `SaveProgress` runs at the start of every day: `SaveGame|CreateSaveGameObject`, a cast, the setters, one `Utilities|Array|Add` per turret on the save object's array getters, then `SaveGame|SaveGametoSlot`. `TryLoadSave` accepts a save only if the slot exists, the object casts to `BP_BeaconSave` and its version is between 1 and the game mode's `CurrentSaveVersion`. `RestoreTurret` finds the turret type whose display name matches the saved name, so a save survives the type list being reordered; a name that no longer exists is skipped. Defaults such as the slot name and the version are set on the class default object. Lighthouse and turret health are not saved: the ticket lists night, resources and turrets. The save was read back for the checks by loading the slot in editor Python. `read_graph_dsl` prints the save object's setter as `Variables|Default|SetNightNumber` and the turret's `TypeName` getter as `Interchange|Node|GetTypeName`; both are the right nodes, which was confirmed by loading the slot in editor Python with `GameplayStatics.load_game_from_slot` and reading the five properties. To test a newer save, `CurrentSaveVersion` was set to 99 on the class default object for one run and back to 1.

### F-053: LoadGameFromSlot crashes the engine on a file that is not a save

- **Ticket:** #15
- **Capability:** SaveGame
- **Tool used:** none exists that can check a file before it is loaded
- **Outcome:** no tool
- **Fallback used:** none: C++ would close the gap and was not taken (see notes)
- **Notes:** A save file that held 1120 bytes of plain text crashed the editor when the game loaded it: "Assertion failed ... UnrealNames.cpp ... FName's 1023 max length exceeded. Got 1936287859 characters". The engine treats a file without the `GVAS` tag as an old-format save and reads a string length from its first bytes. No Blueprint node can read a file's bytes to check the tag first (searched for file, JSON and load-from-memory nodes; only `Utilities|Paths|FileExists` exists). The other kinds of bad save are safe: an empty file, a save cut to half its length, a file of zeros and a save with a newer version all return nothing or fail the version check, and the game starts a new one. The cut and zeroed files each log one engine warning, "Failed to find object 'Class '". Because of the crash the menu no longer loads the save to decide whether to offer Continue; it only asks whether the slot exists, and loads when Continue is pressed. A foreign file then cannot crash the game at launch, and New Game replaces it. An unreadable save therefore still shows Continue, which falls back to a new game. Closing the gap needs a C++ check of the first four bytes, or a text save format. C++ is an allowed fallback, but it would end Beacon being a Blueprint-only project, the same cost that F-030 weighed, so it was left for a person to decide. The project owner accepted the gap on 2026-11-24.

### F-054: after a crash the editor waits on a dialog and the MCP server never starts

- **Ticket:** #15
- **Capability:** agent workflow
- **Tool used:** none; the server was down
- **Outcome:** no tool
- **Fallback used:** none: the restore record was moved aside from a shell and the editor started again
- **Notes:** Relaunching the editor after the crash in F-053 left the process running with no MCP server: the health check was refused for several minutes and the log stopped at frame 0. `(Get-Process UnrealEditor).MainWindowTitle` read "Restore Packages", the modal dialog that offers to restore autosaved packages, which blocks start-up until someone answers it. The agent cannot click it, since every MCP tool lives inside the blocked process. The record of what to restore is `Saved/Autosaves/PackageRestoreData.json`; it listed one template Blueprint that nobody had edited (F-024). Renaming that file and starting the editor again went straight to the project. Read the file before moving it: if it lists real work, a person should answer the dialog. Delete a test save that crashes the game before relaunching, or the next PIE run crashes too.

### F-055: rewriting an event with the DSL leaves its old nodes in the graph

- **Ticket:** #11 (found during the review of #11 to #15)
- **Capability:** Blueprint graph authoring
- **Tool used:** `BlueprintTools.write_graph_dsl`, `find_nodes`, `get_node_infos`, `delete_node`, `read_graph_dsl`
- **Outcome:** worked with a workaround
- **Fallback used:** script client (`Tools/mcp/graph_orphans.py`)
- **Notes:** F-018 says that writing an event again replaces its old chain. It does, by disconnecting the old chain from the event: the old nodes stay in the graph, wired to each other and to nothing that runs. `read_graph_dsl` starts from the entry points, so it does not show them, and the Blueprint compiles without a warning. #11 claimed the `PrintString` nodes were gone on the strength of the read-back; `find_nodes` with the title `Print` still found six of them, in the game mode's `Notify` and the creature's and turret's event graphs. None could run. Across five Blueprints 132 nodes were unreachable, 59 of the 91 in the creature's event graph. `graph_orphans.py` lists the nodes that no event, input action event or function entry reaches by exec links, plus the value nodes that only they read, and deletes them with `--delete`. `find_nodes` with `entry_points_only` does not return Enhanced Input action events, so the script decides what an entry point is from the pins: an exec output and no exec input. After the deletion every affected graph read back the same DSL as before, and a search of every graph of every Beacon Blueprint found no print or debug-draw node. Run the script after rewriting a graph.

### F-056: a minimised editor hides every widget, and the first click after it comes back can be lost

- **Ticket:** #11 (found during the final checks of #11 to #15)
- **Capability:** PIE control
- **Tool used:** `SlateInspectorToolset.Snapshot`, `Windows`, `Click`
- **Outcome:** worked with a workaround
- **Fallback used:** script client (`Tools/mcp/beacon_mcp.py`)
- **Notes:** While the editor's window is minimised the server still answers, but `Windows` with `action: "list"` returns an empty list and `Snapshot` an empty string, so the console box cannot be found and nothing can be typed, clicked or captured. The other toolsets keep working: graphs were searched, edited, compiled and saved with the window minimised. The client now reports an empty snapshot as a minimised window. After the window was restored, the first `verify` run failed: `Click` on the menu's button returned true and the game stayed on the menu. The next run passed, as did a repeat of the same case, so the click that brought the window to the front was probably swallowed. `start_game` no longer presses the button once and assumes: it reads the game state, clicks while the menu is up, presses the skip key only once the intro is playing, and waits through the hand-off. It also survives a skip that arrives too early, since the intro then plays out inside the time allowed.

