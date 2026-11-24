#include "BeaconWaveSim.h"

#include "Math/RandomStream.h"

namespace
{
	// Successive spawns are turned by the golden angle, which spreads any number of them evenly round the circle.
	constexpr double GoldenAngleRadians = 2.39996322972865332;

	struct FSpawn
	{
		double Time = 0.0;
		const FBeaconSimCreatureType* Type = nullptr;
	};

	struct FCreature
	{
		const FBeaconSimCreatureType* Type = nullptr;
		FVector2D Position = FVector2D::ZeroVector;
		double Health = 0.0;
		double NextAttackTime = 0.0;
		/** Index of the turret a turret hunter is after, or INDEX_NONE for the lighthouse. */
		int32 TargetTurret = INDEX_NONE;
	};

	struct FTurretState
	{
		double Health = 0.0;
		double NextFireTime = 0.0;
		bool bStanding = true;
	};

	/** Index of the nearest element that passes the filter, or INDEX_NONE. */
	template <typename ElementType, typename PositionOf, typename Filter>
	int32 FindNearest(TConstArrayView<ElementType> Elements, const FVector2D& From, PositionOf&& GetPosition, Filter&& Passes)
	{
		int32 Nearest = INDEX_NONE;
		double NearestDistanceSquared = TNumericLimits<double>::Max();
		for (int32 Index = 0; Index < Elements.Num(); ++Index)
		{
			if (!Passes(Index))
			{
				continue;
			}
			const double DistanceSquared = FVector2D::DistSquared(From, GetPosition(Elements[Index]));
			if (DistanceSquared < NearestDistanceSquared)
			{
				NearestDistanceSquared = DistanceSquared;
				Nearest = Index;
			}
		}
		return Nearest;
	}

	/** The wave director's timetable: when each creature of the night appears, and of which type. */
	TArray<FSpawn> BuildSchedule(TConstArrayView<FBeaconSimWave> Waves, double CountScale, TArray<FBeaconSimWaveResult>& OutWaves)
	{
		TArray<FSpawn> Schedule;
		double Time = 0.0;
		for (int32 WaveIndex = 0; WaveIndex < Waves.Num(); ++WaveIndex)
		{
			const FBeaconSimWave& Wave = Waves[WaveIndex];
			check(!Wave.Creatures.IsEmpty());
			FBeaconSimWaveResult& WaveResult = OutWaves.AddDefaulted_GetRef();
			WaveResult.Creatures = BeaconWaveSim::CreaturesInWave(Wave, CountScale);
			for (int32 Index = 0; Index < WaveResult.Creatures; ++Index)
			{
				if (Index > 0)
				{
					Time += Wave.SpawnInterval;
				}
				const FBeaconSimCreatureType& Type = Wave.Creatures[Index % Wave.Creatures.Num()];
				Schedule.Add({Time, &Type});
				WaveResult.CreatureHealth += Type.MaxHealth;
			}
			Time += Wave.DelayBeforeNext;
		}
		return Schedule;
	}
} // namespace

int32 BeaconWaveSim::CreaturesInWave(const FBeaconSimWave& Wave, double CountScale)
{
	// The director spawns one creature before it compares the count, so a wave is never empty.
	return FMath::Max(1, FMath::RoundToInt32(Wave.Count * CountScale));
}

FBeaconSimResult BeaconWaveSim::Simulate(
	TConstArrayView<FBeaconSimWave> Waves, TConstArrayView<FBeaconSimTurret> Turrets, const FBeaconSimRules& Rules)
{
	check(Rules.TimeStep > 0.0);

	FBeaconSimResult Result;
	const TArray<FSpawn> Schedule = BuildSchedule(Waves, Rules.CountScale, Result.Waves);
	Result.CreaturesTotal = Schedule.Num();
	for (const FBeaconSimWaveResult& Wave : Result.Waves)
	{
		Result.TotalCreatureHealth += Wave.CreatureHealth;
	}
	Result.Turrets.SetNum(Turrets.Num());

	TArray<FTurretState> TurretStates;
	for (const FBeaconSimTurret& Turret : Turrets)
	{
		TurretStates.Add({Turret.Health});
	}
	const auto TurretPosition = [](const FBeaconSimTurret& Turret) {
		return Turret.Position;
	};
	const auto TurretStands = [&TurretStates](int32 Index) {
		return TurretStates[Index].bStanding;
	};

	FRandomStream RandomBearings(Rules.BearingSeed.Get(0));
	TArray<FCreature> Creatures;
	double LighthouseHealth = Rules.LighthouseHealth;
	int32 NextSpawn = 0;
	double Time = 0.0;
	int64 CreatureChecks = 0;

	for (int64 Step = 0;; ++Step)
	{
		Time = Step * Rules.TimeStep;

		for (; NextSpawn < Schedule.Num() && Schedule[NextSpawn].Time <= Time; ++NextSpawn)
		{
			const double Bearing =
				Rules.BearingSeed.IsSet() ? RandomBearings.FRandRange(0.0, UE_DOUBLE_TWO_PI) : NextSpawn * GoldenAngleRadians;
			FCreature& Creature = Creatures.AddDefaulted_GetRef();
			Creature.Type = Schedule[NextSpawn].Type;
			Creature.Position = Rules.SpawnRadius * FVector2D(FMath::Cos(Bearing), FMath::Sin(Bearing));
			Creature.Health = Creature.Type->MaxHealth;
		}

		CreatureChecks += Creatures.Num();
		for (FCreature& Creature : Creatures)
		{
			if (Creature.Type->bHuntsTurrets && (Creature.TargetTurret == INDEX_NONE || !TurretStates[Creature.TargetTurret].bStanding))
			{
				Creature.TargetTurret = FindNearest(Turrets, Creature.Position, TurretPosition, TurretStands);
			}
			const bool bAfterTurret = Creature.TargetTurret != INDEX_NONE;
			const FVector2D Goal = bAfterTurret ? Turrets[Creature.TargetTurret].Position : FVector2D::ZeroVector;
			const double StandOff = bAfterTurret ? Rules.TurretStandOff : Rules.LighthouseStandOff;

			const FVector2D ToGoal = Goal - Creature.Position;
			const double StillToWalk = ToGoal.Size() - StandOff;
			if (StillToWalk > UE_KINDA_SMALL_NUMBER)
			{
				const double Walked = FMath::Min(Creature.Type->Speed * Rules.TimeStep, StillToWalk);
				Creature.Position += ToGoal.GetSafeNormal() * Walked;
			}
			else if (Time >= Creature.NextAttackTime)
			{
				Creature.NextAttackTime = Time + FMath::Max(Creature.Type->AttackInterval, Rules.TimeStep);
				if (bAfterTurret)
				{
					FTurretState& Turret = TurretStates[Creature.TargetTurret];
					Turret.Health -= Creature.Type->AttackDamage;
					if (Turret.Health <= 0.0)
					{
						Turret.bStanding = false;
						Result.Turrets[Creature.TargetTurret].bDestroyed = true;
					}
				}
				else
				{
					LighthouseHealth = FMath::Max(0.0, LighthouseHealth - Creature.Type->AttackDamage);
				}
			}
		}
		if (LighthouseHealth <= 0.0)
		{
			Result.Outcome = EBeaconSimOutcome::Loss;
			break;
		}

		for (int32 TurretIndex = 0; TurretIndex < Turrets.Num(); ++TurretIndex)
		{
			FTurretState& State = TurretStates[TurretIndex];
			if (!State.bStanding || Time < State.NextFireTime)
			{
				continue;
			}
			const FBeaconSimTurret& Turret = Turrets[TurretIndex];
			CreatureChecks += Creatures.Num();
			const int32 TargetIndex = FindNearest(TConstArrayView<FCreature>(Creatures), Turret.Position, [](const FCreature& Creature) {
				return Creature.Position;
			}, [](int32) { return true; });
			if (TargetIndex == INDEX_NONE
				|| FVector2D::DistSquared(Turret.Position, Creatures[TargetIndex].Position) > FMath::Square(Turret.Range))
			{
				continue;
			}
			State.NextFireTime = Time + FMath::Max(Turret.FireInterval, Rules.TimeStep);
			FCreature& Target = Creatures[TargetIndex];
			const double Removed = FMath::Min(Turret.Damage, Target.Health);
			Target.Health -= Removed;
			Result.Turrets[TurretIndex].DamageDealt += Removed;
			Result.Turrets[TurretIndex].ShotsFired += 1;
			Result.TurretDamageDealt += Removed;
			if (Target.Health <= 0.0)
			{
				Creatures.RemoveAtSwap(TargetIndex);
				Result.CreaturesKilled += 1;
			}
		}
		if (NextSpawn == Schedule.Num() && Creatures.IsEmpty())
		{
			Result.Outcome = EBeaconSimOutcome::Win;
			break;
		}
		Result.bRanOutOfWork = CreatureChecks > Rules.MaxCreatureChecks;
		if (Time >= Rules.MaxSeconds || Result.bRanOutOfWork)
		{
			Result.Outcome = EBeaconSimOutcome::Undecided;
			break;
		}
	}

	Result.DurationSeconds = Time;
	Result.LighthouseHealthRemaining = LighthouseHealth;
	for (const FBeaconSimTurret& Turret : Turrets)
	{
		Result.TurretDamageCapacity += Turret.Damage / FMath::Max(Turret.FireInterval, Rules.TimeStep) * Time;
	}
	return Result;
}
