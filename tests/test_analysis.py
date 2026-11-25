import os
import warnings
from pathlib import Path

import pytest

from core.analysis import NOTES, analyze
from tests.samples import configured
from tests.synth import write_chord, write_click_track, write_m4a


def test_reports_the_tempo_of_a_click_track(tmp_path):
    song = write_click_track(tmp_path / "clicks.wav", bpm=120)

    result = analyze(song)

    assert result.bpm == pytest.approx(120, abs=1)


def test_reads_the_tempo_of_an_m4a_song(tmp_path):
    clicks = write_click_track(tmp_path / "clicks.wav", bpm=120)
    song = write_m4a(tmp_path / "clicks.m4a", clicks)

    result = analyze(song)

    assert result.bpm == pytest.approx(120, abs=1)


def _relative_key(key: str) -> str:
    tonic, mode = key.split()
    i = NOTES.index(tonic)
    if mode == "minor":
        return f"{NOTES[(i + 3) % 12]} major"
    return f"{NOTES[(i - 3) % 12]} minor"


# Labels come from the producers' own file names, so they are a sanity check, not gospel.
# Which songs to use is configured outside the repository: see tests/samples.py.
LABELED_SONGS = configured("labeled") or [None]


@pytest.mark.real_audio
@pytest.mark.parametrize("entry", LABELED_SONGS, ids=lambda e: "not-configured" if e is None else e["file"])
def test_matches_the_label_on_a_real_song(entry):
    folder = os.environ.get("WIHOK_SAMPLES")
    if entry is None or not folder:
        pytest.skip("real songs are not configured (see tests/samples.py) or WIHOK_SAMPLES is not set")
    pattern, expected_bpm, expected_key = entry["file"], entry["bpm"], entry.get("key")
    matches = sorted(Path(folder).glob(pattern))
    if not matches:
        pytest.skip(f"no file matches {pattern!r}")

    result = analyze(matches[0])

    if abs(result.bpm - expected_bpm) > 2:
        # The app has a half/double button, so this is a warning, not a failure.
        octave_errors = (expected_bpm * 2, expected_bpm / 2)
        if any(abs(result.bpm - b) <= 2 for b in octave_errors):
            warnings.warn(f"{matches[0].name}: got {result.bpm:.1f} BPM, label {expected_bpm} (half/double)")
        else:
            pytest.fail(f"got {result.bpm:.1f} BPM, label {expected_bpm}")

    if expected_key and result.key != expected_key:
        if result.key == _relative_key(expected_key):
            warnings.warn(f"{matches[0].name}: got {result.key}, label {expected_key} (relative key)")
        else:
            pytest.fail(f"got {result.key} (confidence {result.key_confidence:.2f}), label {expected_key}")


def test_reports_a_minor_for_an_a_minor_chord(tmp_path):
    # A2 bass + A3, C4, E4
    song = write_chord(tmp_path / "am.wav", [45, 57, 60, 64])

    result = analyze(song)

    assert result.key == "A minor"
