#pragma once

#include "BeaconBalanceData.h"
#include "CoreMinimal.h"
#include "Templates/ValueOrError.h"
#include "ToolsetRegistry/ToolsetDefinition.h"

#include "BeaconBalanceToolset.generated.h"

/** One turret of a layout: which type, and where it stands. */
USTRUCT(BlueprintType)
struct FBeaconTurretPlacement
{
	GENERATED_BODY()

	/** Display name of the turret type, as the build menu shows it (for example "Sentry"). Case is ignored. */
	UPROPERTY(BlueprintReadWrite, Category = "BeaconBalanceToolset")
	FString Type;

	/** World X in centimetres. The lighthouse stands at the origin. */
	UPROPERTY(BlueprintReadWrite, Category = "BeaconBalanceToolset")
	double X = 0.0;

	/** World Y in centimetres. */
	UPROPERTY(BlueprintReadWrite, Category = "BeaconBalanceToolset")
	double Y = 0.0;
};

/** What one wave of the night sends. */
USTRUCT(BlueprintType)
struct FBeaconWaveFigures
{
	GENERATED_BODY()

	/** Number of the wave within the night, starting at 1. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	int32 Wave = 0;

	/** Creatures the wave spawns. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	int32 Creatures = 0;

	/** Summed health of those creatures. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double CreatureHealth = 0.0;
};

/** What one turret of the layout did, averaged over the simulated nights. */
USTRUCT(BlueprintType)
struct FBeaconTurretFigures
{
	GENERATED_BODY()

	/** Display name of the turret's type. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	FString Type;

	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double X = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double Y = 0.0;

	/** The type's damage divided by its fire interval. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double DamagePerSecond = 0.0;

	/** Creature health this turret removed, as a mean over the trials. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double DamageDealt = 0.0;

	/** Shots this turret fired, as a mean over the trials. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double ShotsFired = 0.0;

	/** Share of the trials, from 0 to 1, in which a creature destroyed this turret. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double DestroyedChance = 0.0;
};

UENUM(BlueprintType)
enum class EBeaconPredictedOutcome : uint8
{
	/** Every creature died and the lighthouse stands. */
	Win,
	/** The lighthouse fell. */
	Loss,
	/** Neither happened within half an hour of game time. */
	Undecided,
};

/**
 * Balance figures for one night against one turret layout. The game spawns each creature at a random
 * bearing, so the night is simulated several times with different bearings; the figures that depend on
 * how a night goes are means over those trials.
 */
USTRUCT(BlueprintType)
struct FBeaconWaveSimulation
{
	GENERATED_BODY()

	/** The night that was asked for. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	int32 Night = 0;

	/** The night data asset the game plays for that night. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	FString NightData;

	/** Multiplier on every wave's creature count. Above 1 only for nights past the last authored one. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double CountScale = 1.0;

	/** Creatures the night spawns in total. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	int32 TotalCreatures = 0;

	/** Summed health of every creature the night spawns. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double TotalCreatureHealth = 0.0;

	/** How many times the night was simulated. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	int32 Trials = 0;

	/** The outcome of most trials. A tie goes to the worse outcome. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	EBeaconPredictedOutcome PredictedOutcome = EBeaconPredictedOutcome::Undecided;

	/** Share of the trials, from 0 to 1, that were won. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double WinChance = 0.0;

	/** Creature health the turrets removed over the night, as a mean over the trials. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double TotalTurretDamage = 0.0;

	/** What the turrets would deal if every one fired without pause for the whole night, as a mean over the trials. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double TurretDamageCapacity = 0.0;

	/** Lighthouse health when the outcome was decided, as a mean over the trials. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double LighthouseHealthRemaining = 0.0;

	/** Creatures the turrets killed, as a mean over the trials. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double CreaturesKilled = 0.0;

	/** Game seconds from the first spawn until the outcome was decided, as a mean over the trials. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double DurationSeconds = 0.0;

	/** Turrets that creatures destroyed, as a mean over the trials. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	double TurretsLost = 0.0;

	/** One entry per wave, in play order. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	TArray<FBeaconWaveFigures> Waves;

	/** One entry per turret of the layout, in the order given. */
	UPROPERTY(BlueprintReadOnly, Category = "BeaconBalanceToolset")
	TArray<FBeaconTurretFigures> Turrets;
};

/// Balance tools for Beacon, the wave defence game in this project: they score the game's wave and
/// turret data without playing it.
UCLASS()
class UBeaconBalanceToolset : public UToolsetDefinition
{
	GENERATED_BODY()

public:
	/**
	 * Predicts how one night of Beacon goes against a turret layout, without playing it.
	 * Reads the wave, creature and turret data the game plays from, as currently loaded in the editor, then
	 * steps a model of the night: creatures spawn on the wave schedule, walk straight to the lighthouse (or to
	 * the nearest turret, for a type that hunts turrets) and attack; each turret shoots the nearest creature in
	 * range. The player is not modelled, so this is the night as the turrets alone would fight it.
	 * The game spawns each creature at a random bearing, so the model plays the night 20 times with different
	 * bearings and reports the share it won and the mean of each figure. The same request gives the same answer.
	 * Use it to compare layouts or to see the effect of a data change before running the game.
	 * Raises an error if the night is not between 1 and 50, if a turret type is not one of the game's types,
	 * or if there are more than 32 turrets.
	 * @param Night The night to simulate, starting at 1. Nights past the last authored one replay it with more creatures, as the game does.
	 * @param Turrets The layout: one entry per turret. May be empty.
	 * @return Total creature health, turret damage dealt and available, the predicted outcome and chance of a win, and a breakdown by wave
	 * and by turret.
	 */
	UFUNCTION(meta = (AICallable), Category = "BeaconBalanceToolset")
	static FBeaconWaveSimulation SimulateWave(int32 Night, const TArray<FBeaconTurretPlacement>& Turrets);

	// The limits keep the slowest request, a late night that a large layout holds for the full half hour
	// of game time, to a few seconds: the tool runs on the editor's main thread.
	/** The highest night SimulateWave accepts. */
	static constexpr int32 MaxNight = 50;
	/** The most turrets SimulateWave accepts in one layout. */
	static constexpr int32 MaxTurrets = 32;
	/** How many times SimulateWave plays the night, each with its own spawn bearings. */
	static constexpr int32 Trials = 20;

	/**
	 * SimulateWave over data that has already been read: checks the request, runs the trials and fills in
	 * the figures. Returns the sentence to report if the request is not valid.
	 */
	static TValueOrError<FBeaconWaveSimulation, FString> SimulateWaveWithData(
		const FBeaconBalanceData& Data, int32 Night, TConstArrayView<FBeaconTurretPlacement> Turrets);
};
