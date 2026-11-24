#include "BeaconWaveSim.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	const EAutomationTestFlags WaveSimTestFlags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter;

	/** Walks 3200 - 510 = 2690 cm at 269 cm/s: ten seconds to the lighthouse. */
	FBeaconSimCreatureType Walker()
	{
		FBeaconSimCreatureType Type;
		Type.Name = TEXT("Walker");
		Type.MaxHealth = 50.0;
		Type.Speed = 269.0;
		Type.AttackDamage = 5.0;
		Type.AttackInterval = 1.0;
		return Type;
	}

	FBeaconSimWave WaveOf(int32 Count, const FBeaconSimCreatureType& Type)
	{
		FBeaconSimWave Wave;
		Wave.Count = Count;
		Wave.SpawnInterval = 2.0;
		Wave.Creatures.Add(Type);
		return Wave;
	}

	/** Ten damage every half second, reaching the whole island from the lighthouse. */
	FBeaconSimTurret TurretAt(double X, double Y)
	{
		FBeaconSimTurret Turret;
		Turret.Position = FVector2D(X, Y);
		Turret.Range = 4000.0;
		Turret.Damage = 10.0;
		Turret.FireInterval = 0.5;
		Turret.Health = 60.0;
		return Turret;
	}
} // namespace

BEGIN_DEFINE_SPEC(FBeaconWaveSimSpec, "Beacon.WaveSim", WaveSimTestFlags)
END_DEFINE_SPEC(FBeaconWaveSimSpec)

void FBeaconWaveSimSpec::Define()
{
	It("spawns the scaled count of a wave, rounded, and never fewer than one", [this]() {
		FBeaconSimWave Wave = WaveOf(9, Walker());
		TestEqual(TEXT("unscaled"), BeaconWaveSim::CreaturesInWave(Wave, 1.0), 9);
		TestEqual(TEXT("13.5 rounds up"), BeaconWaveSim::CreaturesInWave(Wave, 1.5), 14);
		Wave.Count = 0;
		TestEqual(TEXT("an empty wave still spawns one"), BeaconWaveSim::CreaturesInWave(Wave, 1.0), 1);
	});

	It("loses the lighthouse to a single creature when no turret stands", [this]() {
		const TArray<FBeaconSimWave> Waves = {WaveOf(1, Walker())};
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, {}, FBeaconSimRules());

		TestTrue(TEXT("outcome is a loss"), Result.Outcome == EBeaconSimOutcome::Loss);
		TestEqual(TEXT("lighthouse health"), Result.LighthouseHealthRemaining, 0.0);
		TestEqual(TEXT("kills"), Result.CreaturesKilled, 0);
		// Ten seconds of walking, then twenty hits a second apart, the first on arrival.
		TestEqual(TEXT("duration"), Result.DurationSeconds, 29.0, 0.1);
		TestEqual(TEXT("total creature health"), Result.TotalCreatureHealth, 50.0);
	});

	It("wins when a turret kills every creature before it arrives", [this]() {
		const TArray<FBeaconSimWave> Waves = {WaveOf(3, Walker())};
		const TArray<FBeaconSimTurret> Turrets = {TurretAt(0.0, 0.0)};
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, Turrets, FBeaconSimRules());

		TestTrue(TEXT("outcome is a win"), Result.Outcome == EBeaconSimOutcome::Win);
		TestEqual(TEXT("lighthouse health"), Result.LighthouseHealthRemaining, 100.0);
		TestEqual(TEXT("kills"), Result.CreaturesKilled, 3);
		TestEqual(TEXT("creatures"), Result.CreaturesTotal, 3);
		TestEqual(TEXT("damage dealt equals the health sent"), Result.TurretDamageDealt, 150.0);
		TestEqual(TEXT("five shots a creature"), Result.Turrets[0].ShotsFired, 15);
		// Five shots half a second apart for each: the first dies at 2.0, the second at 4.5, the third at 7.0.
		TestEqual(TEXT("duration"), Result.DurationSeconds, 7.0, 0.1);
		TestEqual(TEXT("capacity is twenty a second for the whole night"), Result.TurretDamageCapacity, 140.0, 2.0);
	});

	It("leaves a turret idle when nothing comes within its range", [this]() {
		const TArray<FBeaconSimWave> Waves = {WaveOf(1, Walker())};
		FBeaconSimTurret Turret = TurretAt(0.0, 0.0);
		Turret.Range = 300.0;
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, {Turret}, FBeaconSimRules());

		TestTrue(TEXT("outcome is a loss"), Result.Outcome == EBeaconSimOutcome::Loss);
		TestEqual(TEXT("shots"), Result.Turrets[0].ShotsFired, 0);
		TestEqual(TEXT("damage"), Result.TurretDamageDealt, 0.0);
	});

	It("counts only the health a shot removes, not the damage beyond it", [this]() {
		const TArray<FBeaconSimWave> Waves = {WaveOf(1, Walker())};
		FBeaconSimTurret Turret = TurretAt(0.0, 0.0);
		Turret.Damage = 80.0;
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, {Turret}, FBeaconSimRules());

		TestEqual(TEXT("one shot"), Result.Turrets[0].ShotsFired, 1);
		TestEqual(TEXT("damage dealt"), Result.Turrets[0].DamageDealt, 50.0);
	});

	It("sends a turret hunter to destroy the turret before the lighthouse", [this]() {
		FBeaconSimCreatureType Hunter = Walker();
		Hunter.MaxHealth = 100000.0;
		Hunter.AttackDamage = 30.0;
		Hunter.bHuntsTurrets = true;
		const TArray<FBeaconSimWave> Waves = {WaveOf(1, Hunter)};
		// Out past the lighthouse from where the first creature spawns, so the hunter must walk on to reach it.
		const TArray<FBeaconSimTurret> Turrets = {TurretAt(-1000.0, 0.0)};
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, Turrets, FBeaconSimRules());

		TestTrue(TEXT("turret destroyed"), Result.Turrets[0].bDestroyed);
		TestTrue(TEXT("outcome is a loss"), Result.Outcome == EBeaconSimOutcome::Loss);
		// 4000 cm to the turret's stand point, two hits, 290 cm back to the lighthouse's, four hits.
		TestEqual(TEXT("duration"), Result.DurationSeconds, 4000.0 / 269.0 + 1.0 + 290.0 / 269.0 + 3.0, 0.2);
	});

	It("leaves the lighthouse alone while a turret hunter is busy with a turret", [this]() {
		FBeaconSimCreatureType Hunter = Walker();
		Hunter.bHuntsTurrets = true;
		const TArray<FBeaconSimWave> Waves = {WaveOf(1, Hunter)};
		FBeaconSimTurret Turret = TurretAt(-1000.0, 0.0);
		Turret.Range = 100.0;
		Turret.Health = 1.0e9;
		FBeaconSimRules Rules;
		Rules.MaxSeconds = 60.0;
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, {Turret}, Rules);

		TestTrue(TEXT("outcome is undecided"), Result.Outcome == EBeaconSimOutcome::Undecided);
		TestEqual(TEXT("lighthouse health"), Result.LighthouseHealthRemaining, 100.0);
		TestEqual(TEXT("duration is the time allowed"), Result.DurationSeconds, 60.0, 0.1);
	});

	It("plays waves in order, cycling through each wave's creature types", [this]() {
		FBeaconSimCreatureType Heavy = Walker();
		Heavy.MaxHealth = 200.0;
		FBeaconSimWave First = WaveOf(3, Walker());
		First.Creatures.Add(Heavy);
		First.DelayBeforeNext = 6.0;
		const TArray<FBeaconSimWave> Waves = {First, WaveOf(2, Heavy)};
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, {}, FBeaconSimRules());

		TestEqual(TEXT("waves"), Result.Waves.Num(), 2);
		TestEqual(TEXT("first wave creatures"), Result.Waves[0].Creatures, 3);
		TestEqual(TEXT("first wave health: walker, heavy, walker"), Result.Waves[0].CreatureHealth, 300.0);
		TestEqual(TEXT("second wave health"), Result.Waves[1].CreatureHealth, 400.0);
		TestEqual(TEXT("creatures"), Result.CreaturesTotal, 5);
		TestEqual(TEXT("total creature health"), Result.TotalCreatureHealth, 700.0);
	});

	It("holds the next wave back by the delay after the last spawn", [this]() {
		FBeaconSimWave First = WaveOf(1, Walker());
		First.DelayBeforeNext = 6.0;
		const TArray<FBeaconSimWave> Waves = {First, WaveOf(1, Walker())};
		const TArray<FBeaconSimTurret> Turrets = {TurretAt(0.0, 0.0)};
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, Turrets, FBeaconSimRules());

		// The second creature spawns at six seconds and dies to the fifth shot two seconds later.
		TestEqual(TEXT("duration"), Result.DurationSeconds, 8.0, 0.1);
	});

	It("spawns more creatures when the count is scaled", [this]() {
		const TArray<FBeaconSimWave> Waves = {WaveOf(4, Walker())};
		FBeaconSimRules Rules;
		Rules.CountScale = 2.0;
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, {}, Rules);

		TestEqual(TEXT("creatures"), Result.CreaturesTotal, 8);
		TestEqual(TEXT("total creature health"), Result.TotalCreatureHealth, 400.0);
	});

	It("spawns at random bearings when given a seed, the same ones for the same seed", [this]() {
		const TArray<FBeaconSimWave> Waves = {WaveOf(1, Walker())};
		// Out on one side, so the turret fires only if the creature happens to walk past.
		FBeaconSimTurret Turret = TurretAt(2000.0, 0.0);
		Turret.Range = 1200.0;
		TSet<int32> ShotCounts;
		for (int32 Seed = 0; Seed < 20; ++Seed)
		{
			FBeaconSimRules Rules;
			Rules.BearingSeed = Seed;
			const FBeaconSimResult First = BeaconWaveSim::Simulate(Waves, {Turret}, Rules);
			const FBeaconSimResult Again = BeaconWaveSim::Simulate(Waves, {Turret}, Rules);
			TestEqual(TEXT("same seed, same shots"), First.Turrets[0].ShotsFired, Again.Turrets[0].ShotsFired);
			TestEqual(TEXT("same seed, same duration"), First.DurationSeconds, Again.DurationSeconds);
			ShotCounts.Add(First.Turrets[0].ShotsFired);
		}

		TestTrue(TEXT("different seeds send the creature different ways"), ShotCounts.Num() > 1);
	});

	It("stops at its work limit when the night would never end", [this]() {
		FBeaconSimCreatureType Statue = Walker();
		Statue.Speed = 0.0;
		const TArray<FBeaconSimWave> Waves = {WaveOf(10, Statue)};
		FBeaconSimRules Rules;
		Rules.MaxCreatureChecks = 5000;
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(Waves, {}, Rules);

		TestTrue(TEXT("ran out of work"), Result.bRanOutOfWork);
		TestTrue(TEXT("outcome is undecided"), Result.Outcome == EBeaconSimOutcome::Undecided);
		TestTrue(TEXT("long before the time limit"), Result.DurationSeconds < 60.0);
	});

	It("gives the same answer for the same input", [this]() {
		const TArray<FBeaconSimWave> Waves = {WaveOf(12, Walker())};
		FBeaconSimTurret Turret = TurretAt(600.0, 0.0);
		Turret.Range = 1200.0;
		const FBeaconSimResult First = BeaconWaveSim::Simulate(Waves, {Turret}, FBeaconSimRules());
		const FBeaconSimResult Second = BeaconWaveSim::Simulate(Waves, {Turret}, FBeaconSimRules());

		TestEqual(TEXT("duration"), First.DurationSeconds, Second.DurationSeconds);
		TestEqual(TEXT("damage"), First.TurretDamageDealt, Second.TurretDamageDealt);
		TestEqual(TEXT("lighthouse health"), First.LighthouseHealthRemaining, Second.LighthouseHealthRemaining);
	});
}

#endif
