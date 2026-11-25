"""A stand-in for the Demucs process, used where the test is about our behaviour, not Demucs."""
from pathlib import Path

import numpy as np
import soundfile as sf

from core.separator import RunOutcome


def demucs_wrote_its_stems(cmd: list[str]) -> RunOutcome:
    """Do what `python -m demucs --two-stems=vocals ...` does on success: write two stems under -o."""
    out_dir = Path(cmd[cmd.index("-o") + 1])
    song = Path(cmd[-1])
    stems = out_dir / "htdemucs" / song.stem
    stems.mkdir(parents=True, exist_ok=True)
    silence = np.zeros((4410, 2), dtype="float32")
    sf.write(stems / "vocals.wav", silence, 44100)
    sf.write(stems / "no_vocals.wav", silence, 44100)
    return RunOutcome(returncode=0, stderr="")
