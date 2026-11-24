"""Synthesise Beacon's placeholder sound effects as WAV files.

The Unreal MCP has no tool that authors or imports audio, so the sounds are
made here from sine sweeps and noise, then imported by
Tools/editor_python/import_sfx.py.

Usage (repo root):
  python Tools/audio/make_sfx.py Saved/BeaconSfx
"""

from __future__ import annotations

import math
import random
import sys
import wave
from collections.abc import Callable
from pathlib import Path

SAMPLE_RATE = 44100
# Fade applied to both ends of every sound, so playback never starts or stops on a step.
EDGE_FADE_SECONDS = 0.004
PEAK_16_BIT = 32767


def sweep(start_hz: float, end_hz: float, seconds: float) -> list[float]:
    """A sine wave whose pitch slides from one frequency to another."""
    count = int(seconds * SAMPLE_RATE)
    samples = []
    phase = 0.0
    for index in range(count):
        frequency = start_hz + (end_hz - start_hz) * index / count
        phase += 2 * math.pi * frequency / SAMPLE_RATE
        samples.append(math.sin(phase))
    return samples


def noise(seconds: float, seed: int) -> list[float]:
    """White noise that is the same on every run."""
    generator = random.Random(seed)  # noqa: S311 (not cryptography: repeatable noise for a sound effect)
    return [generator.uniform(-1.0, 1.0) for _ in range(int(seconds * SAMPLE_RATE))]


def decay(samples: list[float], rate: float) -> list[float]:
    """Fade a sound out exponentially; a higher rate is a shorter tail."""
    return [sample * math.exp(-rate * index / SAMPLE_RATE) for index, sample in enumerate(samples)]


def mix(first: list[float], second: list[float], second_level: float) -> list[float]:
    longest = max(len(first), len(second))
    padded_first = first + [0.0] * (longest - len(first))
    padded_second = second + [0.0] * (longest - len(second))
    return [a + b * second_level for a, b in zip(padded_first, padded_second, strict=True)]


def finish(samples: list[float], level: float) -> list[float]:
    """Scale to a peak level and fade both edges to silence."""
    peak = max(abs(sample) for sample in samples)
    fade = int(EDGE_FADE_SECONDS * SAMPLE_RATE)
    last = len(samples) - 1
    return [
        sample / peak * level * min(1.0, index / fade, (last - index) / fade)
        for index, sample in enumerate(samples)
    ]


def shot() -> list[float]:
    """A short falling zap with a noise crack, for the player's weapon and the turrets."""
    body = decay(sweep(900.0, 180.0, 0.14), 22.0)
    crack = decay(noise(0.05, seed=1), 90.0)
    return finish(mix(body, crack, 0.6), 0.8)


def hit() -> list[float]:
    """A dull thud, for a shot landing on a creature."""
    body = decay(sweep(240.0, 90.0, 0.09), 35.0)
    grit = decay(noise(0.03, seed=2), 120.0)
    return finish(mix(body, grit, 0.4), 0.7)


def death() -> list[float]:
    """A longer falling tone over a burst of noise, for a creature dying."""
    body = decay(sweep(420.0, 55.0, 0.45), 7.0)
    burst = decay(noise(0.3, seed=3), 14.0)
    return finish(mix(body, burst, 0.5), 0.9)


SOUNDS: dict[str, Callable[[], list[float]]] = {"SFX_Shot": shot, "SFX_Hit": hit, "SFX_Death": death}


def write_wav(path: Path, samples: list[float]) -> None:
    """Write samples in the range -1 to 1 as a mono 16-bit WAV file."""
    frames = b"".join(
        round(max(-1.0, min(1.0, sample)) * PEAK_16_BIT).to_bytes(2, "little", signed=True)
        for sample in samples
    )
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(frames)


def write_all(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for name, make in SOUNDS.items():
        path = folder / f"{name}.wav"
        write_wav(path, make())
        written.append(path)
    return written


if __name__ == "__main__":
    if len(sys.argv) != 2:  # noqa: PLR2004 (the program name and one folder)
        sys.exit(__doc__)
    for wav_path in write_all(Path(sys.argv[1])):
        print(wav_path)
