"""Save every unsaved Beacon map, actor and asset package.

`AssetTools.save_assets` on a map skips changed actors unless the map package
itself is dirty, and no MCP tool can save a level's external actor files on
their own (finding F-015). Run this after editing a level:
  python Tools/mcp/beacon_mcp.py py Tools/editor_python/save_dirty.py
The last log line starts with SAVEDIRTY and gives the counts before and after.

Only packages under /Game/Beacon are saved. `BlueprintTools.read_graph_dsl`
marks the Blueprint it reads as dirty (finding F-024), so reading a template
Blueprint would otherwise rewrite a file nobody changed.
"""

import unreal

# Beacon's own content, including the per-actor files of its levels.
OWNED_ROOTS = ("/Game/Beacon/", "/Game/__ExternalActors__/Beacon/", "/Game/__ExternalObjects__/Beacon/")

utils = unreal.EditorLoadingAndSavingUtils


def dirty_packages() -> list[unreal.Package]:
    return list(utils.get_dirty_map_packages()) + list(utils.get_dirty_content_packages())


def owned(package: unreal.Package) -> bool:
    return package.get_name().startswith(OWNED_ROOTS)


before = dirty_packages()
to_save = [package for package in before if owned(package)]
saved = utils.save_packages(to_save, only_dirty=True) if to_save else True
after = [package for package in dirty_packages() if owned(package)]
skipped = sorted(package.get_name() for package in before if not owned(package))
print(f"SAVEDIRTY ok={saved} saved={len(to_save)} skipped={skipped} after={len(after)}")
