"""Create the creature Blackboard and Behaviour Tree assets.

The Unreal MCP's Behaviour Tree toolset can only inspect a tree, so this is the
editor Python fallback (finding F-017). It runs inside the editor:
  python Tools/mcp/beacon_mcp.py py Tools/editor_python/build_creature_ai.py
Running it again rebuilds the assets in place. The last log line starts with
BUILDAI and says what was written.

Each tree is one Sequence that restarts when it ends:
  find a target and a point to stand at -> walk there -> hit the target once
The find and attack steps are Blueprint task classes, authored through the MCP.
"""

import unreal

AI_FOLDER = "/Game/Beacon/AI"
BLACKBOARD = "BB_Creature"
ATTACK_TASK = "BTTask_AttackTarget"
# Tree name -> the Blueprint task that chooses its target.
TREES = {
    "BT_Creature": "BTTask_FindLighthouse",
}
# How close to the stand point MoveTo must get, in cm. The attack task's range
# check (BP_Creature.AttackRange) must be larger than this.
ACCEPTABLE_RADIUS = 60.0


def load_or_create(name: str, asset_class: type, factory: unreal.Factory) -> unreal.Object:
    path = f"{AI_FOLDER}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, AI_FOLDER, asset_class, factory)


def blackboard_entry(blackboard: unreal.BlackboardData, name: str, key_type: str) -> unreal.BlackboardEntry:
    # The key type classes are not exposed to Python by name, so load them by path.
    key_class = unreal.load_class(None, f"/Script/AIModule.BlackboardKeyType_{key_type}")
    entry = unreal.BlackboardEntry()
    entry.set_editor_property("entry_name", name)
    entry.set_editor_property("key_type", unreal.new_object(key_class, outer=blackboard))
    return entry


def build_blackboard() -> unreal.BlackboardData:
    blackboard = load_or_create(BLACKBOARD, unreal.BlackboardData, unreal.BlackboardDataFactory())
    blackboard.set_editor_property(
        "keys",
        [
            blackboard_entry(blackboard, "TargetActor", "Object"),
            blackboard_entry(blackboard, "MoveGoal", "Vector"),
        ],
    )
    return blackboard


def blueprint_task(tree: unreal.BehaviorTree, name: str) -> unreal.BTTaskNode:
    task_class = unreal.load_class(None, f"{AI_FOLDER}/{name}.{name}_C")
    task = unreal.new_object(task_class, outer=tree)
    task.set_editor_property("node_name", name.removeprefix("BTTask_"))
    return task


def move_to_goal(tree: unreal.BehaviorTree) -> unreal.BTTask_MoveTo:
    move = unreal.new_object(unreal.BTTask_MoveTo, outer=tree)
    move.set_editor_property("node_name", "Move to stand point")
    # Edit the existing selector so its allowed key types are kept.
    key = move.get_editor_property("blackboard_key")
    key.set_editor_property("selected_key_name", "MoveGoal")
    move.set_editor_property("blackboard_key", key)
    # In 5.8 the radius is a "value or blackboard key" struct, not a plain float.
    radius = move.get_editor_property("acceptable_radius")
    radius.set_editor_property("default_value", ACCEPTABLE_RADIUS)
    move.set_editor_property("acceptable_radius", radius)
    return move


def build_tree(name: str, find_task: str, blackboard: unreal.BlackboardData) -> unreal.BehaviorTree:
    tree = load_or_create(name, unreal.BehaviorTree, unreal.BehaviorTreeFactory())
    tree.set_editor_property("blackboard_asset", blackboard)
    sequence = unreal.new_object(unreal.BTComposite_Sequence, outer=tree)
    sequence.set_editor_property("node_name", "Attack target")
    steps = [blueprint_task(tree, find_task), move_to_goal(tree), blueprint_task(tree, ATTACK_TASK)]
    children = []
    for step in steps:
        child = unreal.BTCompositeChild()
        child.set_editor_property("child_task", step)
        children.append(child)
    sequence.set_editor_property("children", children)
    tree.set_editor_property("root_node", sequence)
    return tree


def main() -> None:
    blackboard = build_blackboard()
    written = [blackboard.get_path_name()]
    unreal.EditorAssetLibrary.save_loaded_asset(blackboard)
    for name, find_task in TREES.items():
        tree = build_tree(name, find_task, blackboard)
        unreal.EditorAssetLibrary.save_loaded_asset(tree)
        written.append(tree.get_path_name())
    print("BUILDAI wrote " + ", ".join(written))


main()
