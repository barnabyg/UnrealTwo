"""Print where the island's PCG scatter put its rocks and foliage, as one JSON log line.

Runs inside the editor, with or without play-in-editor running:
  python Tools/mcp/beacon_mcp.py py Tools/editor_python/scatter_state.py
The line starts with SCATTERSTATE. Positions are in centimetres, rounded.
"""

import json

import unreal


def scatter_world() -> unreal.World:
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    return editor.get_game_world() or editor.get_editor_world()


def instances(component: unreal.InstancedStaticMeshComponent) -> list[list[int]]:
    points = []
    for index in range(component.get_instance_count()):
        location = component.get_instance_transform(index, world_space=True).translation
        points.append([round(location.x), round(location.y), round(location.z)])
    return points


def read_state() -> dict[str, object]:
    seed = None
    meshes: dict[str, list[list[int]]] = {}
    collision: dict[str, str] = {}
    # Beacon has one scatter volume; with more, the seed and profiles reported are the last one's.
    for volume in unreal.GameplayStatics.get_all_actors_of_class(scatter_world(), unreal.PCGVolume):
        pcg = volume.get_component_by_class(unreal.PCGComponent)
        if pcg is None:
            continue
        seed = pcg.get_editor_property("seed")
        for component in volume.get_components_by_class(unreal.InstancedStaticMeshComponent):
            mesh = component.static_mesh.get_name() if component.static_mesh else "none"
            meshes.setdefault(mesh, []).extend(instances(component))
            collision[mesh] = str(component.get_collision_profile_name())
    return {"seed": seed, "meshes": meshes, "collision": collision}


print("SCATTERSTATE " + json.dumps(read_state()))
