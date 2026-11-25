import pytest

from core.audio import FfmpegMissing
from core.model import ModelDownloadFailed
from core.pipeline import process_song
from core.separator import RunOutcome
from tests.fakes import demucs_wrote_its_stems
from tests.synth import write_click_track


class CountingRunner:
    def __init__(self):
        self.calls = 0

    def __call__(self, cmd, cancel):
        self.calls += 1
        return demucs_wrote_its_stems(cmd)


def test_processes_a_new_song_end_to_end(tmp_path):
    song = write_click_track(tmp_path / "beat.wav", bpm=120)
    runner, stages = CountingRunner(), []

    result = process_song(
        song, tmp_path / "Wihok", device="cuda", runner=runner, on_stage=stages.append, model_cached=lambda: True
    )

    assert result.reused is False
    assert result.vocals.exists() and result.instrumental.exists()
    assert result.directory == result.vocals.parent
    assert result.analysis.bpm == pytest.approx(120, abs=1)
    assert stages == ["separating", "analyzing"]
    assert runner.calls == 1


def test_the_first_run_says_the_model_is_being_downloaded(tmp_path):
    song = write_click_track(tmp_path / "beat.wav", bpm=120)
    stages = []

    process_song(
        song, tmp_path / "Wihok", device="cuda", runner=CountingRunner(), on_stage=stages.append,
        model_cached=lambda: False,
    )

    assert stages == ["downloading_model", "analyzing"]


def test_a_failed_first_run_is_reported_as_a_download_problem(tmp_path):
    song = write_click_track(tmp_path / "beat.wav", bpm=120)

    def offline(cmd, cancel):
        return RunOutcome(returncode=1, stderr="ConnectionError: could not reach huggingface.co")

    with pytest.raises(ModelDownloadFailed):
        process_song(song, tmp_path / "Wihok", device="cuda", runner=offline, model_cached=lambda: False)


def test_the_same_failure_is_not_blamed_on_the_download_once_the_model_is_cached(tmp_path):
    song = write_click_track(tmp_path / "beat.wav", bpm=120)

    def broken(cmd, cancel):
        return RunOutcome(returncode=1, stderr="something else went wrong")

    with pytest.raises(Exception) as caught:
        process_song(song, tmp_path / "Wihok", device="cuda", runner=broken, model_cached=lambda: True)

    assert not isinstance(caught.value, ModelDownloadFailed)


def test_an_m4a_song_is_refused_up_front_when_ffmpeg_is_missing(tmp_path, monkeypatch):
    song = tmp_path / "song.m4a"
    song.write_bytes(b"not decoded: the check happens before anything is read")
    monkeypatch.setenv("PATH", "")
    runner = CountingRunner()

    with pytest.raises(FfmpegMissing):
        process_song(song, tmp_path / "Wihok", device="cuda", runner=runner)

    assert runner.calls == 0
    assert not (tmp_path / "Wihok").exists()


def test_a_song_that_was_already_processed_is_not_separated_again(tmp_path):
    song = write_click_track(tmp_path / "beat.wav", bpm=120)
    runner, stages = CountingRunner(), []
    base = tmp_path / "Wihok"
    process_song(song, base, device="cuda", runner=runner, model_cached=lambda: True)

    result = process_song(
        song, base, device="cuda", runner=runner, on_stage=stages.append, model_cached=lambda: True
    )

    assert result.reused is True
    assert stages == ["reusing", "analyzing"]
    assert runner.calls == 1
