#pragma once

#include "BeaconWaveSim.h"
#include "CoreMinimal.h"
#include "Templates/ValueOrError.h"

/** A turret type, as BP_TurretType describes it. */
struct FBeaconTurretTypeData
{
	FString Name;
	double Range = 0.0;
	double Damage = 0.0;
	double FireInterval = 1.0;
};

/** One authored night: the name of its BP_NightData asset and its waves. */
struct FBeaconNightData
{
	FString Name;
	TArray<FBeaconSimWave> Waves;
};

/** The game's balance data, read out of its Blueprint data assets. */
struct FBeaconBalanceData
{
	/** The game mode's nights, in play order. */
	TArray<FBeaconNightData> Nights;
	/** The game mode's turret types, in build menu order. */
	TArray<FBeaconTurretTypeData> TurretTypes;
	/** Health of a freshly placed turret. */
	double TurretHealth = 0.0;
	/** The rules as the Blueprints set them. CountScale is left at one; it depends on the night asked for. */
	FBeaconSimRules Rules;
};

namespace BeaconBalanceData
{
	/**
	 * Reads the nights, waves, creature types and turret types that BP_BeaconGameMode plays from.
	 * The objects are read as loaded, so an edit made in the editor counts before it is saved.
	 * Returns a sentence saying what is missing or malformed if the data cannot be read.
	 */
	TValueOrError<FBeaconBalanceData, FString> Load();
} // namespace BeaconBalanceData
