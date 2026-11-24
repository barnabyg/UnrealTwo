using UnrealBuildTool;

// Editor-only tools for Beacon, exposed to agents through the Unreal MCP.
public class BeaconEditor : ModuleRules
{
	public BeaconEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PrivateDependencyModuleNames.AddRange(new string[] { "AssetRegistry", "Core", "CoreUObject", "Engine", "ToolsetRegistry" });
	}
}
