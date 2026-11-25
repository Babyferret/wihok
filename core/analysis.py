from pathlib import Path

import librosa
import numpy as np

from core.audio import load_mono
from core.models import AnalysisResult

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl-Schmuckler key profiles
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def analyze(path: Path) -> AnalysisResult:
    y, sr = load_mono(path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    key, confidence = _detect_key(y, sr)
    return AnalysisResult(
        bpm=float(np.atleast_1d(tempo)[0]),
        key=key,
        key_confidence=confidence,
    )


def _detect_key(y: np.ndarray, sr: int) -> tuple[str, float]:
    harmonic = librosa.effects.harmonic(y)
    chroma = librosa.feature.chroma_cqt(y=harmonic, sr=sr).mean(axis=1)
    best_score, best_key = -2.0, ""
    for tonic in range(12):
        for profile, mode in ((MAJOR, "major"), (MINOR, "minor")):
            score = np.corrcoef(chroma, np.roll(profile, tonic))[0, 1]
            if score > best_score:
                best_score, best_key = score, f"{NOTES[tonic]} {mode}"
    return best_key, float(best_score)
