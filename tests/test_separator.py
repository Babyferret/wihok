import os
import sys
import threading
import time
from pathlib import Path

import librosa
import numpy as np
import pytest
import soundfile as sf
import torch

from core.separator import OutOfGpuMemory, RunOutcome, SeparationCancelled, run_demucs, separate
from tests.fakes import demucs_wrote_its_stems
from tests.samples import configured
from tests.synth import write_chord


def _device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _mel_db(path: Path, seconds: float = 60.0) -> np.ndarray:
    y, sr = librosa.load(path, sr=22050, mono=True, duration=seconds)
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=512, n_mels=64)
    return librosa.power_to_db(mel, ref=np.max)


def _similarity(a: np.ndarray, b: np.ndarray) -> float:
    frames = min(a.shape[1], b.shape[1])
    return float(np.corrcoef(a[:, :frames].ravel(), b[:, :frames].ravel())[0, 1])


# Each pair is a full song with vocals and the same song with the vocals removed.
# Which songs to use is configured outside the repository: see tests/samples.py.
REFERENCE_PAIRS = configured("pairs") or [None]


@pytest.mark.real_audio
@pytest.mark.parametrize("pair", REFERENCE_PAIRS, ids=lambda p: "not-configured" if p is None else p["full"])
def test_karaoke_is_closer_to_the_instrumental_than_the_full_mix_is(tmp_path, pair):
    folder = os.environ.get("WIHOK_SAMPLES")
    if pair is None or not folder:
        pytest.skip("real songs are not configured (see tests/samples.py) or WIHOK_SAMPLES is not set")
    full_song, reference_song = Path(folder) / pair["full"], Path(folder) / pair["reference"]
    if not (full_song.exists() and reference_song.exists()):
        pytest.skip("pair not found")

    result = separate(full_song, tmp_path / "out", device=_device())

    ref = _mel_db(reference_song)
    karaoke_similarity = _similarity(_mel_db(result.instrumental), ref)
    full_mix_similarity = _similarity(_mel_db(full_song), ref)
    assert karaoke_similarity > full_mix_similarity, (
        f"karaoke {karaoke_similarity:.3f} vs full mix {full_mix_similarity:.3f}"
    )


def test_retries_with_a_smaller_segment_when_the_gpu_runs_out_of_memory(tmp_path):
    song = write_chord(tmp_path / "song.wav", [60], seconds=2)
    commands, notices = [], []

    def runner(cmd, cancel):
        commands.append(cmd)
        if len(commands) == 1:
            return RunOutcome(returncode=1, stderr="torch.OutOfMemoryError: CUDA out of memory")
        return demucs_wrote_its_stems(cmd)

    result = separate(song, tmp_path / "out", device="cuda", runner=runner, on_notice=notices.append)

    assert result.vocals.exists() and result.instrumental.exists()
    assert "--segment" not in commands[0]
    assert "--segment" in commands[1]
    assert all(cmd[cmd.index("-d") + 1] == "cuda" for cmd in commands)
    assert notices, "the user must be told why this is taking a second try"


def test_a_packaged_app_starts_demucs_through_itself(tmp_path, monkeypatch):
    # In the .exe there is no python.exe to run `-m demucs`, so the app calls itself with --demucs.
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    song = write_chord(tmp_path / "song.wav", [60], seconds=2)
    commands = []

    def runner(cmd, cancel):
        commands.append(cmd)
        return demucs_wrote_its_stems(cmd)

    separate(song, tmp_path / "out", device="cuda", runner=runner)

    assert commands[0][:2] == [sys.executable, "--demucs"]
    assert "-m" not in commands[0]
    assert "--two-stems=vocals" in commands[0]


def test_never_falls_back_to_the_cpu_on_its_own(tmp_path):
    song = write_chord(tmp_path / "song.wav", [60], seconds=2)
    commands = []

    def runner(cmd, cancel):
        commands.append(cmd)
        return RunOutcome(returncode=1, stderr="CUDA out of memory")

    with pytest.raises(OutOfGpuMemory):
        separate(song, tmp_path / "out", device="cuda", runner=runner)

    assert all(cmd[cmd.index("-d") + 1] == "cuda" for cmd in commands)
    assert len(commands) > 1, "smaller segments should have been tried first"


def test_cancelling_removes_only_the_files_of_that_job(tmp_path):
    song = write_chord(tmp_path / "song.wav", [60], seconds=2)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "earlier-result.wav").write_bytes(b"keep me")

    def runner(cmd, cancel):
        demucs_wrote_its_stems(cmd)  # half-finished output is already on disk
        cancel.set()
        return RunOutcome(returncode=-9, stderr="")

    import threading
    with pytest.raises(SeparationCancelled):
        separate(song, out_dir, device="cuda", runner=runner, cancel=threading.Event())

    assert sorted(p.name for p in out_dir.iterdir()) == ["earlier-result.wav"]


def test_the_demucs_process_can_print_any_file_name_whatever_the_windows_code_page(monkeypatch):
    # Many PCs pipe Python's output through a legacy code page such as cp1252, which cannot encode a Thai or
    # Japanese file name. Demucs prints the path of the song, so it crashed on such names.
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    command = [sys.executable, "-c", "print('Separated tracks will be stored in ไทย 日本語')"]

    outcome = run_demucs(command, threading.Event())

    assert outcome.returncode == 0, outcome.stderr


def test_the_runner_kills_the_process_when_cancelled():
    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    started = time.monotonic()

    outcome = run_demucs([sys.executable, "-c", "import time; time.sleep(20)"], cancel)

    assert time.monotonic() - started < 10
    assert outcome.returncode != 0


def test_splits_a_song_into_acapella_and_karaoke(tmp_path):
    song = write_chord(tmp_path / "song.wav", [45, 57, 60, 64], seconds=8)

    result = separate(song, tmp_path / "out", device=_device())

    assert result.vocals.name == "song_acapella.wav"
    assert result.instrumental.name == "song_karaoke.wav"
    for stem in (result.vocals, result.instrumental):
        assert sf.info(stem).duration == pytest.approx(8.0, abs=0.1)
