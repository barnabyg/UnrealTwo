#include "BeaconBalanceToolset.h"
#include "Modules/ModuleManager.h"
#include "ToolsetRegistry/UToolsetRegistry.h"

// Registering the class is what makes its AICallable functions MCP tools.
class FBeaconEditorModule : public IModuleInterface
{
	virtual void StartupModule() override
	{
		UToolsetRegistry::RegisterToolsetClass(UBeaconBalanceToolset::StaticClass());
	}

	virtual void ShutdownModule() override
	{
		UToolsetRegistry::UnregisterToolsetClass(UBeaconBalanceToolset::StaticClass());
	}
};

IMPLEMENT_MODULE(FBeaconEditorModule, BeaconEditor)
