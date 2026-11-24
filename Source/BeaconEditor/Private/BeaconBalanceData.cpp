#include "BeaconBalanceData.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "UObject/UnrealType.h"

namespace
{
	const TCHAR* const GameModeClassPath = TEXT("/Game/Beacon/Blueprints/BP_BeaconGameMode.BP_BeaconGameMode_C");
	const TCHAR* const LighthouseClassPath = TEXT("/Game/Beacon/Blueprints/BP_Lighthouse.BP_Lighthouse_C");
	const TCHAR* const TurretClassPath = TEXT("/Game/Beacon/Blueprints/BP_Turret.BP_Turret_C");
	const TCHAR* const FindLighthouseTaskPath = TEXT("/Game/Beacon/AI/BTTask_FindLighthouse.BTTask_FindLighthouse_C");
	const TCHAR* const StandBesideTaskPath = TEXT("/Game/Beacon/AI/BTTask_StandBesideTarget.BTTask_StandBesideTarget_C");
	// A behaviour tree that runs this query sends its creature after turrets (see Tools/editor_python/build_creature_ai.py).
	const FName TurretQueryPackage = TEXT("/Game/Beacon/AI/EQS_NearestTurret");
	// The MoveTo node's acceptable radius: a creature stops this far short of its stand point (same script).
	constexpr double MoveAcceptanceRadius = 60.0;

	/**
	 * Reads variables of Blueprint-defined classes by name. The game's data classes exist only as Blueprints,
	 * so C++ has no headers for them. The first failure is kept and every later read returns a default,
	 * which lets a caller read a whole asset and check once.
	 */
	class FBlueprintReader
	{
	public:
		/** The class default object of a Blueprint class, which holds the defaults the game starts from. */
		const UObject* DefaultObject(const TCHAR* ClassPath)
		{
			const UClass* Class = LoadClass<UObject>(nullptr, ClassPath);
			if (Class == nullptr)
			{
				Fail(FString::Printf(TEXT("the Blueprint class %s could not be loaded"), ClassPath));
				return nullptr;
			}
			return Class->GetDefaultObject();
		}

		double Number(const UObject* Object, const TCHAR* Name)
		{
			const FNumericProperty* Property = Find<FNumericProperty>(Object, Name, TEXT("a number"));
			if (Property == nullptr)
			{
				return 0.0;
			}
			const void* Value = Property->ContainerPtrToValuePtr<void>(Object);
			return Property->IsFloatingPoint() ? Property->GetFloatingPointPropertyValue(Value)
											   : static_cast<double>(Property->GetSignedIntPropertyValue(Value));
		}

		FString String(const UObject* Object, const TCHAR* Name)
		{
			const FStrProperty* Property = Find<FStrProperty>(Object, Name, TEXT("a string"));
			return Property != nullptr ? Property->GetPropertyValue_InContainer(Object) : FString();
		}

		/** An object reference variable. A reference left empty is a failure. */
		const UObject* Object(const UObject* Owner, const TCHAR* Name)
		{
			const FObjectPropertyBase* Property = Find<FObjectPropertyBase>(Owner, Name, TEXT("an object reference"));
			if (Property == nullptr)
			{
				return nullptr;
			}
			const UObject* Value = Property->GetObjectPropertyValue_InContainer(Owner);
			if (Value == nullptr)
			{
				Fail(FString::Printf(TEXT("%s.%s is not set"), *Owner->GetName(), Name));
			}
			return Value;
		}

		/** An array of object references. An empty array or an empty entry is a failure. */
		TArray<const UObject*> Objects(const UObject* Owner, const TCHAR* Name)
		{
			TArray<const UObject*> Values;
			const FArrayProperty* Property = Find<FArrayProperty>(Owner, Name, TEXT("an array of object references"));
			if (Property == nullptr)
			{
				return Values;
			}
			const FObjectPropertyBase* Inner = CastField<FObjectPropertyBase>(Property->Inner);
			if (Inner == nullptr)
			{
				Fail(FString::Printf(TEXT("%s.%s is not an array of object references"), *Owner->GetName(), Name));
				return Values;
			}
			FScriptArrayHelper Array(Property, Property->ContainerPtrToValuePtr<void>(Owner));
			for (int32 Index = 0; Index < Array.Num(); ++Index)
			{
				const UObject* Value = Inner->GetObjectPropertyValue(Array.GetRawPtr(Index));
				if (Value == nullptr)
				{
					Fail(FString::Printf(TEXT("%s.%s has an empty entry at index %d"), *Owner->GetName(), Name, Index));
					return {};
				}
				Values.Add(Value);
			}
			if (Values.IsEmpty())
			{
				Fail(FString::Printf(TEXT("%s.%s is empty"), *Owner->GetName(), Name));
			}
			return Values;
		}

		void Fail(FString&& Message)
		{
			if (ErrorMessage.IsEmpty())
			{
				ErrorMessage = MoveTemp(Message);
			}
		}

		bool HasFailed() const
		{
			return !ErrorMessage.IsEmpty();
		}

		const FString& GetError() const
		{
			return ErrorMessage;
		}

	private:
		template <typename PropertyType> const PropertyType* Find(const UObject* Object, const TCHAR* Name, const TCHAR* Expected)
		{
			if (Object == nullptr)
			{
				// The read that produced the null has already recorded why.
				return nullptr;
			}
			const PropertyType* Property = CastField<PropertyType>(Object->GetClass()->FindPropertyByName(Name));
			if (Property == nullptr)
			{
				Fail(
					FString::Printf(
						TEXT("%s (a %s) has no variable %s that is %s"),
						*Object->GetName(),
						*Object->GetClass()->GetName(),
						Name,
						Expected));
			}
			return Property;
		}

		FString ErrorMessage;
	};

	bool RunsTurretQuery(const UObject* BehaviorTree)
	{
		if (BehaviorTree == nullptr)
		{
			return false;
		}
		const IAssetRegistry& AssetRegistry = FAssetRegistryModule::GetRegistry();
		TArray<FName> Dependencies;
		AssetRegistry.GetDependencies(BehaviorTree->GetPackage()->GetFName(), Dependencies);
		return Dependencies.Contains(TurretQueryPackage);
	}

	FBeaconSimCreatureType ReadCreatureType(FBlueprintReader& Reader, const UObject* Asset)
	{
		FBeaconSimCreatureType Type;
		Type.Name = Reader.String(Asset, TEXT("DisplayName"));
		Type.MaxHealth = Reader.Number(Asset, TEXT("MaxHealth"));
		Type.Speed = Reader.Number(Asset, TEXT("Speed"));
		Type.AttackDamage = Reader.Number(Asset, TEXT("AttackDamage"));
		Type.AttackInterval = Reader.Number(Asset, TEXT("AttackInterval"));
		Type.bHuntsTurrets = RunsTurretQuery(Reader.Object(Asset, TEXT("BehaviorTree")));
		return Type;
	}

	FBeaconSimWave ReadWave(FBlueprintReader& Reader, const UObject* Asset)
	{
		FBeaconSimWave Wave;
		Wave.Count = FMath::RoundToInt32(Reader.Number(Asset, TEXT("Count")));
		Wave.SpawnInterval = Reader.Number(Asset, TEXT("SpawnInterval"));
		Wave.DelayBeforeNext = Reader.Number(Asset, TEXT("DelayBeforeNext"));
		for (const UObject* Creature : Reader.Objects(Asset, TEXT("Creatures")))
		{
			Wave.Creatures.Add(ReadCreatureType(Reader, Creature));
		}
		return Wave;
	}

	FBeaconTurretTypeData ReadTurretType(FBlueprintReader& Reader, const UObject* Asset)
	{
		FBeaconTurretTypeData Type;
		Type.Name = Reader.String(Asset, TEXT("DisplayName"));
		Type.Range = Reader.Number(Asset, TEXT("Range"));
		Type.Damage = Reader.Number(Asset, TEXT("Damage"));
		Type.FireInterval = Reader.Number(Asset, TEXT("FireInterval"));
		return Type;
	}
} // namespace

TValueOrError<FBeaconBalanceData, FString> BeaconBalanceData::Load()
{
	FBlueprintReader Reader;
	FBeaconBalanceData Data;

	const UObject* GameMode = Reader.DefaultObject(GameModeClassPath);
	for (const UObject* NightAsset : Reader.Objects(GameMode, TEXT("Nights")))
	{
		FBeaconNightData& Night = Data.Nights.AddDefaulted_GetRef();
		Night.Name = NightAsset->GetName();
		for (const UObject* WaveAsset : Reader.Objects(NightAsset, TEXT("Waves")))
		{
			Night.Waves.Add(ReadWave(Reader, WaveAsset));
		}
	}
	for (const UObject* TurretTypeAsset : Reader.Objects(GameMode, TEXT("TurretTypes")))
	{
		Data.TurretTypes.Add(ReadTurretType(Reader, TurretTypeAsset));
	}

	Data.TurretHealth = Reader.Number(Reader.DefaultObject(TurretClassPath), TEXT("MaxHealth"));
	Data.Rules.LighthouseHealth = Reader.Number(Reader.DefaultObject(LighthouseClassPath), TEXT("MaxHealth"));
	Data.Rules.LighthouseStandOff =
		Reader.Number(Reader.DefaultObject(FindLighthouseTaskPath), TEXT("StandOffDistance")) + MoveAcceptanceRadius;
	Data.Rules.TurretStandOff = Reader.Number(Reader.DefaultObject(StandBesideTaskPath), TEXT("StandOffDistance")) + MoveAcceptanceRadius;

	if (Reader.HasFailed())
	{
		return MakeError(FString::Printf(TEXT("Beacon's balance data could not be read: %s."), *Reader.GetError()));
	}
	return MakeValue(MoveTemp(Data));
}
