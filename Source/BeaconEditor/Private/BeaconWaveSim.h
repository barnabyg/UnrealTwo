#pragma once

#include "CoreMinimal.h"

// A model of one Beacon night with no player: creatures spawn on the wave
// director's schedule, walk in a straight line to their target and attack it,
// while turrets shoot the nearest creature in range. It repeats the rules of the
// Blueprints (BP_BeaconGameMode, BP_Turret, BP_Creature and the behaviour trees)
// in plain C++ so that a night can be scored without playing it. Nothing here
// touches an asset; BeaconBalanceData fills these structs from the game's data.

/** A creature type, as BP_CreatureType describes it. Distances are in centimetres. */
struct FBeaconSimCreatureType
{
	FString Name;
	double MaxHealth = 0.0;
	double Speed = 0.0;
	double AttackDamage = 0.0;
	double AttackInterval = 1.0;
	/** True for a type whose behaviour tree goes for the nearest turret while one stands. */
	bool bHuntsTurrets = false;
};

/** One wave, as BP_WaveData describes it. Creatures are spawned by cycling through the list. */
struct FBeaconSimWave
{
	int32 Count = 0;
	double SpawnInterval = 0.0;
	double DelayBeforeNext = 0.0;
	TArray<FBeaconSimCreatureType> Creatures;
};

/** A placed turret: its type's figures and where it stands, with the lighthouse at the origin. */
struct FBeaconSimTurret
{
	FVector2D Position = FVector2D::ZeroVector;
	double Range = 0.0;
	double Damage = 0.0;
	double FireInterval = 1.0;
	double Health = 0.0;
};

/** Everything about a night that is not a wave or a turret. */
struct FBeaconSimRules
{
	/** Multiplier on every wave's count, as the wave director applies it to nights past the last authored one. */
	double CountScale = 1.0;
	/** Creatures appear on a circle of this radius round the lighthouse. */
	double SpawnRadius = 3200.0;
	double LighthouseHealth = 100.0;
	/** How far from the lighthouse's centre a creature stops to attack it. */
	double LighthouseStandOff = 510.0;
	/** How far from a turret a turret hunter stops to attack it. */
	double TurretStandOff = 200.0;
	/** One step of the model. A turret fires at most once a step, as it fires at most once a frame in the game. */
	double TimeStep = 1.0 / 60.0;
	/** The model gives up and reports Undecided after this much game time. */
	double MaxSeconds = 1800.0;
	/**
	 * Seed for the bearing each creature spawns at, which the game picks at random.
	 * Unset, the bearings are spread evenly instead, so that a single run is a fair sample.
	 */
	TOptional<int32> BearingSeed;
};

enum class EBeaconSimOutcome : uint8
{
	/** Every creature of every wave died and the lighthouse stands. */
	Win,
	/** The lighthouse reached zero health. */
	Loss,
	/** Neither happened within FBeaconSimRules::MaxSeconds. */
	Undecided,
};

struct FBeaconSimTurretResult
{
	/** Creature health this turret removed. Damage beyond a creature's remaining health is not counted. */
	double DamageDealt = 0.0;
	int32 ShotsFired = 0;
	bool bDestroyed = false;
};

struct FBeaconSimWaveResult
{
	int32 Creatures = 0;
	double CreatureHealth = 0.0;
};

struct FBeaconSimResult
{
	EBeaconSimOutcome Outcome = EBeaconSimOutcome::Undecided;
	/** Game time from the first spawn to the moment the outcome was decided. */
	double DurationSeconds = 0.0;
	double LighthouseHealthRemaining = 0.0;
	/** Creatures the whole night would spawn, whether or not it ran that long. */
	int32 CreaturesTotal = 0;
	int32 CreaturesKilled = 0;
	/** Summed health of every creature the night would spawn. */
	double TotalCreatureHealth = 0.0;
	/** Creature health removed by all turrets together. */
	double TurretDamageDealt = 0.0;
	/** What the turrets would deal firing without pause for DurationSeconds. */
	double TurretDamageCapacity = 0.0;
	/** One entry per turret passed in, in the same order. */
	TArray<FBeaconSimTurretResult> Turrets;
	/** One entry per wave passed in, in the same order. */
	TArray<FBeaconSimWaveResult> Waves;
};

namespace BeaconWaveSim
{
	/** How many creatures the wave director spawns for a wave: the scaled count, and never fewer than one. */
	int32 CreaturesInWave(const FBeaconSimWave& Wave, double CountScale);

	/**
	 * Plays the waves against the turrets and reports what happened.
	 * Every wave must list at least one creature type. The result is the same for the same input,
	 * FBeaconSimRules::BearingSeed included.
	 */
	FBeaconSimResult Simulate(
		TConstArrayView<FBeaconSimWave> Waves, TConstArrayView<FBeaconSimTurret> Turrets, const FBeaconSimRules& Rules);
} // namespace BeaconWaveSim
