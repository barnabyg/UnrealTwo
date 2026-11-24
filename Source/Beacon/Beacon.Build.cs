using UnrealBuildTool;

// The game's runtime module. The game itself is Blueprint; this module exists
// because a game target needs a primary game module to link.
public class Beacon : ModuleRules
{
	public Beacon(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
	}
}
