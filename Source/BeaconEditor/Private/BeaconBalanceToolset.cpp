#include "BeaconBalanceToolset.h"

#include "Kismet/KismetSystemLibrary.h"

#include UE_INLINE_GENERATED_CPP_BY_NAME(BeaconBalanceToolset)

namespace
{
	/** The outcome of most trials. A tie goes to the worse outcome: a loss, then no decision. */
	EBeaconPredictedOutcome MostFrequentOutcome(int32 Wins, int32 Losses, int32 Undecided)
	{
		if (Losses >= Wins && Losses >= Undecided)
		{
			return EBeaconPredictedOutcome::Loss;
		}
		return Undecided >= Wins ? EBeaconPredictedOutcome::Undecided : EBeaconPredictedOutcome::Win;
	}

	FString JoinTurretTypeNames(const FBeaconBalanceData& Data)
	{
		TArray<FString> Names;
		for (const FBeaconTurretTypeData& Type : Data.TurretTypes)
		{
			Names.Add(Type.Name);
		}
		return FString::Join(Names, TEXT(", "));
	}
} // namespace

TValueOrError<FBeaconWaveSimulation, FString> UBeaconBalanceToolset::SimulateWaveWithData(
	const FBeaconBalanceData& Data, int32 Night, TConstArrayView<FBeaconTurretPlacement> Turrets)
{
	if (Data.Nights.IsEmpty())
	{
		return MakeError(FString(TEXT("The game has no nights to simulate.")));
	}
	if (Night < 1 || Night > MaxNight)
	{
		return MakeError(
			FString::Printf(
				TEXT(
					"Unknown night %d: the night must be between 1 and %d. Nights 1 to %d have their own data; later nights replay night "
					"%d with more creatures."),
				Night,
				MaxNight,
				Data.Nights.Num(),
				Data.Nights.Num()));
	}
	if (Turrets.Num() > MaxTurrets)
	{
		return MakeError(
			FString::Printf(TEXT("Too many turrets: the layout has %d and the most allowed is %d."), Turrets.Num(), MaxTurrets));
	}

	TArray<FBeaconSimTurret> SimTurrets;
	FBeaconWaveSimulation Figures;
	for (int32 Index = 0; Index < Turrets.Num(); ++Index)
	{
		const FBeaconTurretPlacement& Placement = Turrets[Index];
		const FBeaconTurretTypeData* Type = Data.TurretTypes.FindByPredicate([&Placement](const FBeaconTurretTypeData& Candidate) {
			return Candidate.Name.Equals(Placement.Type, ESearchCase::IgnoreCase);
		});
		if (Type == nullptr)
		{
			return MakeError(
				FString::Printf(
					TEXT("Unknown turret type \"%s\" (turret %d of the layout). The game's turret types are: %s."),
					*Placement.Type,
					Index + 1,
					*JoinTurretTypeNames(Data)));
		}
		// A field left out of the request arrives as zero, so a turret with no position lands inside the lighthouse and is caught here.
		const double FromLighthouse = FVector2D(Placement.X, Placement.Y).Size();
		if (!FMath::IsFinite(FromLighthouse) || FromLighthouse < Data.BuildableInnerRadius || FromLighthouse > Data.BuildableOuterRadius)
		{
			return MakeError(
				FString::Printf(
					TEXT(
						"Turret %d of the layout, at (%s, %s), is not on buildable ground. The lighthouse is at (0, 0) and a turret "
						"stands between %s and %s cm from it."),
					Index + 1,
					*FString::SanitizeFloat(Placement.X, 0),
					*FString::SanitizeFloat(Placement.Y, 0),
					*FString::SanitizeFloat(Data.BuildableInnerRadius, 0),
					*FString::SanitizeFloat(Data.BuildableOuterRadius, 0)));
		}
		FBeaconSimTurret& SimTurret = SimTurrets.AddDefaulted_GetRef();
		SimTurret.Position = FVector2D(Placement.X, Placement.Y);
		SimTurret.Range = Type->Range;
		SimTurret.Damage = Type->Damage;
		SimTurret.FireInterval = Type->FireInterval;
		SimTurret.Health = Data.TurretHealth;

		FBeaconTurretFigures& TurretFigures = Figures.Turrets.AddDefaulted_GetRef();
		TurretFigures.Type = Type->Name;
		TurretFigures.X = Placement.X;
		TurretFigures.Y = Placement.Y;
		TurretFigures.DamagePerSecond = Type->FireInterval > 0.0 ? Type->Damage / Type->FireInterval : 0.0;
	}

	// The wave director's rule: past the last authored night it replays that night, with half as many creatures again each time.
	const FBeaconNightData& NightData = Data.Nights[FMath::Min(Night, Data.Nights.Num()) - 1];
	FBeaconSimRules Rules = Data.Rules;
	Rules.CountScale = 1.0 + 0.5 * FMath::Max(Night - Data.Nights.Num(), 0);

	// The wave data is whatever is loaded in the editor, so it is checked like any other input.
	double NightCreatures = 0.0;
	for (const FBeaconSimWave& Wave : NightData.Waves)
	{
		if (Wave.Creatures.IsEmpty())
		{
			return MakeError(FString::Printf(TEXT("A wave of %s lists no creature types."), *NightData.Name));
		}
		NightCreatures += FMath::Max(1.0, FMath::RoundToDouble(Wave.Count * Rules.CountScale));
	}
	if (NightCreatures > MaxCreatures)
	{
		return MakeError(
			FString::Printf(
				TEXT("Night %d sends %.0f creatures, and the most this tool simulates is %d. Check the Count of the waves in %s."),
				Night,
				NightCreatures,
				MaxCreatures,
				*NightData.Name));
	}

	Figures.Night = Night;
	Figures.NightData = NightData.Name;
	Figures.CountScale = Rules.CountScale;
	Figures.Trials = Trials;

	// The figures hold sums over the trials until the loop ends, and are divided into means after it.
	int32 Wins = 0;
	int32 Losses = 0;
	for (int32 Trial = 0; Trial < Trials; ++Trial)
	{
		Rules.BearingSeed = Trial;
		const FBeaconSimResult Result = BeaconWaveSim::Simulate(NightData.Waves, SimTurrets, Rules);
		if (Result.bRanOutOfWork)
		{
			return MakeError(
				FString::Printf(
					TEXT(
						"Night %d could not be simulated: after %.0f seconds of game time the model had reached no outcome and "
						"used all the work it is allowed. Check %s for a creature type that never reaches its target or does no damage."),
					Night,
					Result.DurationSeconds,
					*NightData.Name));
		}

		Wins += Result.Outcome == EBeaconSimOutcome::Win ? 1 : 0;
		Losses += Result.Outcome == EBeaconSimOutcome::Loss ? 1 : 0;
		Figures.TotalTurretDamage += Result.TurretDamageDealt;
		Figures.TurretDamageCapacity += Result.TurretDamageCapacity;
		Figures.LighthouseHealthRemaining += Result.LighthouseHealthRemaining;
		Figures.CreaturesKilled += Result.CreaturesKilled;
		Figures.DurationSeconds += Result.DurationSeconds;
		for (int32 Index = 0; Index < Result.Turrets.Num(); ++Index)
		{
			FBeaconTurretFigures& TurretFigures = Figures.Turrets[Index];
			TurretFigures.DamageDealt += Result.Turrets[Index].DamageDealt;
			TurretFigures.ShotsFired += Result.Turrets[Index].ShotsFired;
			if (Result.Turrets[Index].bDestroyed)
			{
				TurretFigures.DestroyedChance += 1.0;
				Figures.TurretsLost += 1.0;
			}
		}
		if (Trial > 0)
		{
			continue;
		}
		// What the night sends does not depend on the bearings, so the first trial's count stands for all.
		Figures.TotalCreatures = Result.CreaturesTotal;
		Figures.TotalCreatureHealth = Result.TotalCreatureHealth;
		for (int32 Index = 0; Index < Result.Waves.Num(); ++Index)
		{
			FBeaconWaveFigures& WaveFigures = Figures.Waves.AddDefaulted_GetRef();
			WaveFigures.Wave = Index + 1;
			WaveFigures.Creatures = Result.Waves[Index].Creatures;
			WaveFigures.CreatureHealth = Result.Waves[Index].CreatureHealth;
		}
	}
	for (double* Sum :
		 {&Figures.TotalTurretDamage,
		  &Figures.TurretDamageCapacity,
		  &Figures.LighthouseHealthRemaining,
		  &Figures.CreaturesKilled,
		  &Figures.DurationSeconds,
		  &Figures.TurretsLost})
	{
		*Sum /= Trials;
	}
	for (FBeaconTurretFigures& TurretFigures : Figures.Turrets)
	{
		TurretFigures.DamageDealt /= Trials;
		TurretFigures.ShotsFired /= Trials;
		TurretFigures.DestroyedChance /= Trials;
	}
	Figures.WinChance = static_cast<double>(Wins) / Trials;
	Figures.PredictedOutcome = MostFrequentOutcome(Wins, Losses, Trials - Wins - Losses);
	return MakeValue(MoveTemp(Figures));
}

FBeaconWaveSimulation UBeaconBalanceToolset::SimulateWave(int32 Night, const TArray<FBeaconTurretPlacement>& Turrets)
{
	TValueOrError<FBeaconBalanceData, FString> Data = BeaconBalanceData::Load();
	if (Data.HasError())
	{
		UKismetSystemLibrary::RaiseScriptError(Data.GetError());
		return {};
	}
	TValueOrError<FBeaconWaveSimulation, FString> Figures = SimulateWaveWithData(Data.GetValue(), Night, Turrets);
	if (Figures.HasError())
	{
		UKismetSystemLibrary::RaiseScriptError(Figures.GetError());
		return {};
	}
	return Figures.StealValue();
}
