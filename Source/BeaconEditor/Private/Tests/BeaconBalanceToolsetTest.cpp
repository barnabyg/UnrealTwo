#include "BeaconBalanceToolset.h"
#include "BeaconBalanceData.h"
#include "Misc/AutomationTest.h"
#include "ToolsetRegistry/ToolCallExceptionHandler.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	const EAutomationTestFlags BalanceToolsetTestFlags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter;

	/**
	 * Two authored nights of one wave each, and three turret types. A Sentry reaches the whole island from
	 * anywhere near the lighthouse, so what it does is the same whatever bearing the creatures come from.
	 */
	FBeaconBalanceData SampleData()
	{
		FBeaconSimCreatureType Creature;
		Creature.Name = TEXT("Walker");
		Creature.MaxHealth = 50.0;
		Creature.Speed = 269.0;
		Creature.AttackDamage = 5.0;

		FBeaconBalanceData Data;
		for (const int32 Count : {2, 4})
		{
			FBeaconSimWave Wave;
			Wave.Count = Count;
			Wave.SpawnInterval = 1.0;
			Wave.Creatures.Add(Creature);
			FBeaconNightData& Night = Data.Nights.AddDefaulted_GetRef();
			Night.Name = FString::Printf(TEXT("Night_%d"), Data.Nights.Num());
			Night.Waves.Add(Wave);
		}
		Data.TurretTypes.Add({TEXT("Sentry"), 5000.0, 10.0, 0.5});
		Data.TurretTypes.Add({TEXT("Sniper"), 2400.0, 40.0, 2.0});
		Data.TurretTypes.Add({TEXT("Guard"), 1200.0, 10.0, 0.5});
		Data.TurretHealth = 60.0;
		return Data;
	}

	FBeaconTurretPlacement Place(const TCHAR* Type, double X, double Y)
	{
		FBeaconTurretPlacement Placement;
		Placement.Type = Type;
		Placement.X = X;
		Placement.Y = Y;
		return Placement;
	}
} // namespace

BEGIN_DEFINE_SPEC(FBeaconBalanceToolsetSpec, "Beacon.BalanceToolset", BalanceToolsetTestFlags)
END_DEFINE_SPEC(FBeaconBalanceToolsetSpec)

void FBeaconBalanceToolsetSpec::Define()
{
	Describe("SimulateWave over given data", [this]() {
		It("reports the night's totals and what each turret did", [this]() {
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("Sentry"), 600.0, 0.0), Place(TEXT("Sniper"), -600.0, 0.0)};
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 2, Layout);

			if (!TestTrue(TEXT("valid request"), Figures.HasValue()))
			{
				return;
			}
			const FBeaconWaveSimulation& Value = Figures.GetValue();
			TestEqual(TEXT("night"), Value.Night, 2);
			TestEqual(TEXT("night data"), Value.NightData, FString(TEXT("Night_2")));
			TestEqual(TEXT("count scale"), Value.CountScale, 1.0);
			TestEqual(TEXT("creatures"), Value.TotalCreatures, 4);
			TestEqual(TEXT("creature health"), Value.TotalCreatureHealth, 200.0);
			TestEqual(TEXT("trials"), Value.Trials, UBeaconBalanceToolset::Trials);
			TestTrue(TEXT("predicted a win"), Value.PredictedOutcome == EBeaconPredictedOutcome::Win);
			TestEqual(TEXT("won every trial"), Value.WinChance, 1.0);
			TestEqual(TEXT("turret damage equals the health sent"), Value.TotalTurretDamage, 200.0);
			TestEqual(TEXT("kills"), Value.CreaturesKilled, 4.0);
			TestEqual(TEXT("lighthouse health"), Value.LighthouseHealthRemaining, 100.0);
			TestEqual(TEXT("waves"), Value.Waves.Num(), 1);
			TestEqual(TEXT("wave number"), Value.Waves[0].Wave, 1);
			TestEqual(TEXT("turrets"), Value.Turrets.Num(), 2);
			TestEqual(TEXT("sentry damage per second"), Value.Turrets[0].DamagePerSecond, 20.0);
			TestEqual(TEXT("sniper damage per second"), Value.Turrets[1].DamagePerSecond, 20.0);
			TestEqual(TEXT("turret damage adds up"), Value.Turrets[0].DamageDealt + Value.Turrets[1].DamageDealt, Value.TotalTurretDamage);
		});

		It("changes its figures when the wave data changes", [this]() {
			FBeaconBalanceData Data = SampleData();
			const auto Before = UBeaconBalanceToolset::SimulateWaveWithData(Data, 1, {});
			Data.Nights[0].Waves[0].Count = 7;
			const auto After = UBeaconBalanceToolset::SimulateWaveWithData(Data, 1, {});

			TestEqual(TEXT("creatures before"), Before.GetValue().TotalCreatures, 2);
			TestEqual(TEXT("creatures after"), After.GetValue().TotalCreatures, 7);
			TestEqual(TEXT("creature health after"), After.GetValue().TotalCreatureHealth, 350.0);
		});

		It("changes its figures when the turret data changes", [this]() {
			FBeaconBalanceData Data = SampleData();
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("Sentry"), 600.0, 0.0)};
			const auto Before = UBeaconBalanceToolset::SimulateWaveWithData(Data, 1, Layout);
			Data.TurretTypes[0].Damage = 25.0;
			const auto After = UBeaconBalanceToolset::SimulateWaveWithData(Data, 1, Layout);

			TestEqual(TEXT("damage per second before"), Before.GetValue().Turrets[0].DamagePerSecond, 20.0);
			TestEqual(TEXT("damage per second after"), After.GetValue().Turrets[0].DamagePerSecond, 50.0);
			TestTrue(TEXT("fewer shots"), After.GetValue().Turrets[0].ShotsFired < Before.GetValue().Turrets[0].ShotsFired);
		});

		It("gives the chance of a win when the spawn bearings decide the night", [this]() {
			FBeaconBalanceData Data = SampleData();
			Data.Nights[0].Waves[0].Count = 1;
			// A Guard out on one side stops the creature only if it happens to walk past.
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("Guard"), 2000.0, 0.0)};
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(Data, 1, Layout);

			const FBeaconWaveSimulation& Value = Figures.GetValue();
			TestTrue(TEXT("some trials are won"), Value.WinChance > 0.0);
			TestTrue(TEXT("most are lost"), Value.WinChance < 0.5);
			TestTrue(TEXT("predicted a loss"), Value.PredictedOutcome == EBeaconPredictedOutcome::Loss);
			TestEqual(TEXT("mean kills is the chance of the one kill"), Value.CreaturesKilled, Value.WinChance);
			TestEqual(TEXT("mean lighthouse health is all of it for each win"), Value.LighthouseHealthRemaining, 100.0 * Value.WinChance);
		});

		It("gives the same answer when asked again", [this]() {
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("Guard"), 700.0, 0.0)};
			const auto First = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 2, Layout);
			const auto Second = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 2, Layout);

			TestEqual(TEXT("win chance"), First.GetValue().WinChance, Second.GetValue().WinChance);
			TestEqual(TEXT("turret damage"), First.GetValue().TotalTurretDamage, Second.GetValue().TotalTurretDamage);
			TestEqual(TEXT("duration"), First.GetValue().DurationSeconds, Second.GetValue().DurationSeconds);
		});

		It("replays the last authored night with more creatures for later nights", [this]() {
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 4, {});

			TestEqual(TEXT("night data"), Figures.GetValue().NightData, FString(TEXT("Night_2")));
			TestEqual(TEXT("count scale"), Figures.GetValue().CountScale, 2.0);
			TestEqual(TEXT("creatures"), Figures.GetValue().TotalCreatures, 8);
		});

		It("matches a turret type whatever its case", [this]() {
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("sniper"), 0.0, 600.0)};
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 1, Layout);

			TestEqual(TEXT("type as the game names it"), Figures.GetValue().Turrets[0].Type, FString(TEXT("Sniper")));
		});

		It("refuses a night below one or above the limit", [this]() {
			const auto Zero = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 0, {});
			const auto TooHigh = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), UBeaconBalanceToolset::MaxNight + 1, {});

			TestTrue(TEXT("night 0 is an error"), Zero.HasError() && Zero.GetError().Contains(TEXT("Unknown night 0")));
			TestTrue(TEXT("night 51 is an error"), TooHigh.HasError() && TooHigh.GetError().Contains(TEXT("Unknown night 51")));
		});

		It("refuses an unknown turret type and names the known ones", [this]() {
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("Sentry"), 600.0, 0.0), Place(TEXT("Laser"), -600.0, 0.0)};
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 1, Layout);

			if (TestTrue(TEXT("an error"), Figures.HasError()))
			{
				TestTrue(TEXT("names the type"), Figures.GetError().Contains(TEXT("Unknown turret type \"Laser\" (turret 2")));
				TestTrue(TEXT("lists the known types"), Figures.GetError().Contains(TEXT("Sentry, Sniper, Guard")));
			}
		});

		It("refuses a layout with too many turrets", [this]() {
			TArray<FBeaconTurretPlacement> Layout;
			Layout.Init(Place(TEXT("Sentry"), 600.0, 0.0), UBeaconBalanceToolset::MaxTurrets + 1);
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 1, Layout);

			TestTrue(TEXT("an error"), Figures.HasError() && Figures.GetError().Contains(TEXT("Too many turrets")));
		});

		It("refuses a turret with no position, which arrives at the lighthouse's own", [this]() {
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("Sentry"), 600.0, 0.0), Place(TEXT("Sniper"), 0.0, 0.0)};
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 1, Layout);

			if (TestTrue(TEXT("an error"), Figures.HasError()))
			{
				TestTrue(TEXT("names the turret"), Figures.GetError().Contains(TEXT("Turret 2 of the layout, at (0, 0)")));
				TestTrue(TEXT("says where a turret can stand"), Figures.GetError().Contains(TEXT("between 350 and 2800 cm")));
			}
		});

		It("refuses a turret beyond the plateau", [this]() {
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("Sentry"), 0.0, -2900.0)};
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(SampleData(), 1, Layout);

			TestTrue(TEXT("an error"), Figures.HasError() && Figures.GetError().Contains(TEXT("not on buildable ground")));
		});

		It("refuses wave data that sends more creatures than it will simulate", [this]() {
			FBeaconBalanceData Data = SampleData();
			Data.Nights[0].Waves[0].Count = 2000000000;
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(Data, 1, {});

			TestTrue(TEXT("an error"), Figures.HasError() && Figures.GetError().Contains(TEXT("sends 2000000000 creatures")));
		});

		It("refuses a wave that lists no creature types", [this]() {
			FBeaconBalanceData Data = SampleData();
			Data.Nights[0].Waves[0].Creatures.Empty();
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(Data, 1, {});

			TestTrue(TEXT("an error"), Figures.HasError() && Figures.GetError().Contains(TEXT("lists no creature types")));
		});

		It("reports data it cannot simulate within its work limit instead of grinding on", [this]() {
			FBeaconBalanceData Data = SampleData();
			Data.Nights[0].Waves[0].Creatures[0].Speed = 0.0;
			Data.Rules.MaxCreatureChecks = 1000;
			const auto Figures = UBeaconBalanceToolset::SimulateWaveWithData(Data, 1, {});

			TestTrue(TEXT("an error"), Figures.HasError() && Figures.GetError().Contains(TEXT("could not be simulated")));
		});
	});

	Describe("SimulateWave over the game's own data", [this]() {
		It("reads the nights and turret types the game mode plays from", [this]() {
			const TValueOrError<FBeaconBalanceData, FString> Data = BeaconBalanceData::Load();

			if (!TestTrue(TEXT("data loads"), Data.HasValue()))
			{
				AddError(Data.GetError());
				return;
			}
			TestTrue(TEXT("has nights"), Data.GetValue().Nights.Num() > 0);
			TestTrue(TEXT("has turret types"), Data.GetValue().TurretTypes.Num() > 0);
			TestTrue(TEXT("lighthouse has health"), Data.GetValue().Rules.LighthouseHealth > 0.0);
			TestTrue(TEXT("turrets have health"), Data.GetValue().TurretHealth > 0.0);
			bool bSomeTypeHuntsTurrets = false;
			for (const FBeaconNightData& Night : Data.GetValue().Nights)
			{
				for (const FBeaconSimWave& Wave : Night.Waves)
				{
					for (const FBeaconSimCreatureType& Creature : Wave.Creatures)
					{
						TestTrue(TEXT("creature has a name"), !Creature.Name.IsEmpty());
						TestTrue(TEXT("creature moves"), Creature.Speed > 0.0);
						bSomeTypeHuntsTurrets |= Creature.bHuntsTurrets;
					}
				}
			}
			TestTrue(TEXT("the hunter's tree is recognised"), bSomeTypeHuntsTurrets);
		});

		It("predicts a lost lighthouse for the first night with no turrets", [this]() {
			UE::ToolsetRegistry::FToolCallExceptionHandler Errors;
			FBeaconWaveSimulation Figures;
			Errors.CaptureErrorsIn([&Figures]() { Figures = UBeaconBalanceToolset::SimulateWave(1, {}); });

			TestEqual(TEXT("no error"), Errors.GetException(), FString());
			TestTrue(TEXT("predicted a loss"), Figures.PredictedOutcome == EBeaconPredictedOutcome::Loss);
			TestEqual(TEXT("no trial is won"), Figures.WinChance, 0.0);
			TestTrue(TEXT("has creatures"), Figures.TotalCreatures > 0);
			TestEqual(TEXT("no turret damage"), Figures.TotalTurretDamage, 0.0);
		});

		// A raised tool error is also written to the log as a warning, which would otherwise mark the test.
		It("raises a tool error for an unknown turret type", [this]() {
			AddExpectedMessagePlain(TEXT("Unknown turret type"), ELogVerbosity::Warning);
			UE::ToolsetRegistry::FToolCallExceptionHandler Errors;
			const TArray<FBeaconTurretPlacement> Layout = {Place(TEXT("Laser"), 0.0, 0.0)};
			Errors.CaptureErrorsIn([&Layout]() { UBeaconBalanceToolset::SimulateWave(1, Layout); });

			TestTrue(TEXT("names the type"), Errors.GetException().Contains(TEXT("Unknown turret type \"Laser\"")));
		});

		It("raises a tool error for an unknown night", [this]() {
			AddExpectedMessagePlain(TEXT("Unknown night 0"), ELogVerbosity::Warning);
			UE::ToolsetRegistry::FToolCallExceptionHandler Errors;
			Errors.CaptureErrorsIn([]() { UBeaconBalanceToolset::SimulateWave(0, {}); });

			TestTrue(TEXT("names the night"), Errors.GetException().Contains(TEXT("Unknown night 0")));
		});
	});
}

#endif
