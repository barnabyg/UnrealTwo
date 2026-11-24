"""Import Beacon's generated sound effects as SoundWave assets.

No MCP tool authors or imports audio (finding F-043). Make the WAV files
first, then run this inside the editor:
  python Tools/audio/make_sfx.py Saved/BeaconSfx
  python Tools/mcp/beacon_mcp.py py Tools/editor_python/import_sfx.py
The last log line starts with IMPORTSFX and lists the assets that now exist.
"""

from pathlib import Path

import unreal

SOURCE = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / "BeaconSfx"
DESTINATION = "/Game/Beacon/Audio"


def import_task(wav: Path) -> unreal.AssetImportTask:
    task = unreal.AssetImportTask()
    task.filename = str(wav)
    task.destination_path = DESTINATION
    task.automated = True
    task.replace_existing = True
    task.save = True
    return task


tasks = [import_task(wav) for wav in sorted(SOURCE.glob("SFX_*.wav"))]
if not tasks:
    raise RuntimeError(f"no SFX_*.wav files in {SOURCE.as_posix()}: run Tools/audio/make_sfx.py first")
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
imported = sorted(str(path) for task in tasks for path in task.imported_object_paths)
print(f"IMPORTSFX source={SOURCE.as_posix()} wavs={len(tasks)} imported={imported}")
