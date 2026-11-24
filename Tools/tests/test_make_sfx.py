from __future__ import annotations

import wave
from pathlib import Path

import pytest
from make_sfx import SAMPLE_RATE, SOUNDS, write_all, write_wav


@pytest.mark.parametrize("name", sorted(SOUNDS))
def test_each_sound_is_short_audible_and_within_range(name: str) -> None:
    samples = SOUNDS[name]()

    assert 0.05 * SAMPLE_RATE <= len(samples) <= 0.8 * SAMPLE_RATE
    assert max(abs(sample) for sample in samples) <= 1.0
    assert max(abs(sample) for sample in samples) >= 0.3


@pytest.mark.parametrize("name", sorted(SOUNDS))
def test_each_sound_starts_and_ends_quietly_so_it_does_not_click(name: str) -> None:
    samples = SOUNDS[name]()

    assert abs(samples[0]) < 0.05
    assert abs(samples[-1]) < 0.05


def test_sounds_are_the_same_on_every_run() -> None:
    assert SOUNDS["SFX_Death"]() == SOUNDS["SFX_Death"]()


def test_write_wav_makes_a_mono_16_bit_file(tmp_path: Path) -> None:
    path = tmp_path / "tone.wav"

    write_wav(path, [0.0, 0.5, -0.5, 1.0, -1.0])

    with wave.open(str(path), "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, SAMPLE_RATE)
        assert wav.getnframes() == 5
        frames = wav.readframes(5)
    assert int.from_bytes(frames[6:8], "little", signed=True) == 32767
    assert int.from_bytes(frames[8:10], "little", signed=True) == -32767


def test_write_all_writes_one_file_per_sound(tmp_path: Path) -> None:
    written = write_all(tmp_path / "sfx")

    assert sorted(path.name for path in written) == ["SFX_Death.wav", "SFX_Hit.wav", "SFX_Shot.wav"]
    assert all(path.stat().st_size > 1000 for path in written)
