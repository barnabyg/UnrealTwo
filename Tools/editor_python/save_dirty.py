"""Save every unsaved map, actor and asset package.

`AssetTools.save_assets` on a map skips changed actors unless the map package
itself is dirty, and no MCP tool can save a level's external actor files on
their own (finding F-015). Run this after editing a level:
  python Tools/mcp/beacon_mcp.py py Tools/editor_python/save_dirty.py
The last log line starts with SAVEDIRTY and gives the counts before and after.
"""

import unreal

utils = unreal.EditorLoadingAndSavingUtils


def dirty_count() -> int:
    return len(utils.get_dirty_map_packages()) + len(utils.get_dirty_content_packages())


before = dirty_count()
saved = utils.save_dirty_packages(save_map_packages=True, save_content_packages=True)
print(f"SAVEDIRTY ok={saved} before={before} after={dirty_count()}")
