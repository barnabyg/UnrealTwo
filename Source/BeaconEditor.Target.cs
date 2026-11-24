using UnrealBuildTool;

public class BeaconEditorTarget : TargetRules
{
	public BeaconEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.AddRange(new string[] { "Beacon", "BeaconEditor" });
	}
}
