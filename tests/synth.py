"""Synthetic audio for tests. Expected values come from the arguments, not from the code under test."""
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 44100


def write_m4a(path: Path, wav: Path) -> Path:
    """Encode a wav as AAC in an m4a container with FFmpeg. Skips the test when FFmpeg is missing."""
    import shutil
    import subprocess

    import pytest

    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg is not on PATH")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "aac", str(path)], check=True)
    return path


def midi_to_hz(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def write_chord(path: Path, midi_notes: list[int], seconds: float = 12.0) -> Path:
    """A sustained chord; each note has three harmonics so it sounds like an instrument, not a pure tone."""
    t = np.arange(int(SAMPLE_RATE * seconds)) / SAMPLE_RATE
    audio = np.zeros_like(t)
    for note in midi_notes:
        f = midi_to_hz(note)
        for harmonic, gain in ((1, 1.0), (2, 0.5), (3, 0.25)):
            audio += gain * np.sin(2 * np.pi * f * harmonic * t)
    audio = (0.3 * audio / np.max(np.abs(audio))).astype("float32")
    sf.write(path, audio, SAMPLE_RATE)
    return path


def write_click_track(path: Path, bpm: float, seconds: float = 20.0) -> Path:
    """A short 1 kHz click on every beat, silence in between."""
    n = int(SAMPLE_RATE * seconds)
    audio = np.zeros(n, dtype="float32")
    click_len = int(SAMPLE_RATE * 0.02)
    t = np.arange(click_len) / SAMPLE_RATE
    click = (np.sin(2 * np.pi * 1000 * t) * np.exp(-t * 200)).astype("float32")
    interval = SAMPLE_RATE * 60.0 / bpm
    beat = 0
    while True:
        start = int(round(beat * interval))
        if start + click_len > n:
            break
        audio[start:start + click_len] += click
        beat += 1
    sf.write(path, audio, SAMPLE_RATE)
    return path
