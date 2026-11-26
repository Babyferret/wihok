from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

# Formats libsndfile cannot read; they go through FFmpeg.
NEEDS_FFMPEG = {".m4a"}


class FfmpegMissing(RuntimeError):
    """This song's format can only be decoded with FFmpeg, and FFmpeg is not on PATH."""


def ensure_decodable(path: Path) -> None:
    path = Path(path)
    if path.suffix.lower() in NEEDS_FFMPEG and shutil.which("ffmpeg") is None:
        raise FfmpegMissing(f"{path.suffix.lower()} files need FFmpeg, which was not found.")


def load_mono(path: Path) -> tuple[np.ndarray, int]:
    # imported here so that opening the window does not load them (see core.analysis)
    import librosa
    import soundfile as sf

    try:
        return librosa.load(path, sr=None, mono=True)
    except sf.LibsndfileError:
        if shutil.which("ffmpeg") is None:
            raise FfmpegMissing(f"{Path(path).suffix.lower()} files need FFmpeg, which was not found.") from None
        with tempfile.TemporaryDirectory() as tmp:
            decoded = Path(tmp) / "decoded.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ac", "1", str(decoded)],
                check=True, capture_output=True,
            )
            return librosa.load(decoded, sr=None, mono=True)
