from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from core.audio import FfmpegMissing, load_mono
from core.models import AnalysisResult

if TYPE_CHECKING:
    import numpy as np

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl-Schmuckler key profiles
MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def analyze(path: Path) -> AnalysisResult:
    # librosa and numpy are imported here, not at the top: the window imports this module for NOTES alone,
    # and loading them at start-up would cost memory the program holds even while it sits idle.
    import librosa
    import numpy as np

    y, sr = load_mono(path)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    key, confidence = _detect_key(y, sr)
    return AnalysisResult(
        bpm=float(np.atleast_1d(tempo)[0]),
        key=key,
        key_confidence=confidence,
    )


class AnalysisFailed(RuntimeError):
    pass


FFMPEG_MISSING_EXIT_CODE = 3
ANALYSIS_TIMEOUT_SECONDS = 15 * 60  # a song takes seconds; this only stops a stuck process from holding the window busy forever


def analysis_command(song: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--analyze", str(song)]
    return [sys.executable, "-m", "core.analysis", str(song)]


def analyze_separately(song: Path, run: Callable = subprocess.run) -> AnalysisResult:
    """analyze() in a short-lived second process. librosa, numba and scipy hold about a gigabyte once they have
    worked; in the window's own process that would stay until the program is closed, here it is given back."""
    try:
        done = run(analysis_command(song), capture_output=True, text=True, encoding="utf-8", errors="replace",
                   cwd=None if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent,
                   env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},  # as for Demucs: a Thai name in a message
                   timeout=ANALYSIS_TIMEOUT_SECONDS, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:  # subprocess.run has already killed the child
        raise AnalysisFailed(f"the analysis took longer than {ANALYSIS_TIMEOUT_SECONDS // 60} minutes") from None
    except OSError as error:
        raise AnalysisFailed(f"could not start the analysis: {error}") from error
    if done.returncode == FFMPEG_MISSING_EXIT_CODE:
        raise FfmpegMissing(f"{Path(song).suffix.lower()} files need FFmpeg, which was not found.")
    lines = done.stdout.strip().splitlines() if done.returncode == 0 else []
    try:
        reply = json.loads(lines[-1])
        return AnalysisResult(bpm=float(reply["bpm"]), key=str(reply["key"]), key_confidence=float(reply["key_confidence"]))
    except (IndexError, ValueError, KeyError, TypeError):
        raise AnalysisFailed((done.stderr or done.stdout or "no answer").strip()[-800:]) from None


def run_job(arguments: list[str]) -> int:
    """What the second process does: analyse the song and print one JSON line."""
    try:
        result = analyze(Path(arguments[0]))
    except FfmpegMissing:
        return FFMPEG_MISSING_EXIT_CODE
    except Exception:
        try:
            traceback.print_exc()
        except OSError:  # no usable stderr (a windowed build started without a pipe): exit quietly, not with a dialog
            pass
        return 1
    print(json.dumps({"bpm": result.bpm, "key": result.key, "key_confidence": result.key_confidence}))
    return 0


def _detect_key(y: np.ndarray, sr: int) -> tuple[str, float]:
    import librosa
    import numpy as np

    harmonic = librosa.effects.harmonic(y)
    chroma = librosa.feature.chroma_cqt(y=harmonic, sr=sr).mean(axis=1)
    best_score, best_key = -2.0, ""
    for tonic in range(12):
        for profile, mode in ((MAJOR, "major"), (MINOR, "minor")):
            score = np.corrcoef(chroma, np.roll(np.array(profile), tonic))[0, 1]
            if score > best_score:
                best_score, best_key = score, f"{NOTES[tonic]} {mode}"
    return best_key, float(best_score)


if __name__ == "__main__":
    sys.exit(run_job(sys.argv[1:]))
