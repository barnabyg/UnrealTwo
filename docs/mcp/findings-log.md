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
