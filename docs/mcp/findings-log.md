# Unreal MCP findings log

What happened each time Beacon was built through the UE 5.8 Unreal MCP: which tool was used, whether it worked, and what was used instead when it did not. Every ticket appends entries here. The tool names refer to [tool-inventory.md](tool-inventory.md); the planned coverage is in [capability-map.md](capability-map.md).

## Entry format

Add entries at the end, numbered in order. Do not rewrite an old entry when something changes later; add a new one that refers to it.

```markdown
### F-000: one-line summary

- **Ticket:** #n
- **Capability:** the feature area from the capability map
- **Tool used:** `Toolset.tool`, or "none" when no tool exists
- **Outcome:** worked | worked with a workaround | failed | no tool
- **Fallback used:** none | editor Python | C++ | manual step | other MCP tool (say which)
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
- **Capability:** custom tools and fallbacks
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
- **Fallback used:** other: a script client that speaks MCP over HTTP
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

- **Ticket:** #4, found during #5
- **Capability:** level and actor editing
- **Tool used:** `AssetTools.save_assets`, `SceneTools.save_actor`
- **Outcome:** failed
- **Fallback used:** editor Python: `Tools/editor_python/save_dirty.py`, run with `beacon_mcp.py save`
- **Notes:** This corrects F-010. In a level that stores one file per actor, `save_assets` on the map saved the actor files only while the map package itself was dirty (in #4, right after a WorldSettings change). Later actor edits left the map package clean; `save_assets` then returned true and wrote nothing, and `is_dirty` on the map said false, while 54 actor packages were unsaved. The boundary wall swap and the seabed fix from #4 were committed unsaved for that reason. `save_assets` and `save_actor` on the actor packages both fail with "Asset does not exist". The script calls `EditorLoadingAndSavingUtils.save_dirty_packages` and reports the unsaved count before and after. Check `git status` after saving a level.
