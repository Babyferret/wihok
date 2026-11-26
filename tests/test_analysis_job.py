import json
import subprocess

import pytest

from core.analysis import AnalysisFailed, analyze_separately, run_job
from core.audio import FfmpegMissing
from core.models import AnalysisResult
from tests.synth import write_click_track


def _answer(stdout="", returncode=0, stderr=""):
    return lambda command, **kwargs: subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def test_the_job_result_comes_back_as_an_analysis(tmp_path):
    reply = json.dumps({"bpm": 120.5, "key": "A minor", "key_confidence": 0.8})

    result = analyze_separately(tmp_path / "song.mp3", run=_answer("some noise\n" + reply + "\n"))

    assert result == AnalysisResult(bpm=120.5, key="A minor", key_confidence=0.8)


def test_the_song_path_reaches_the_job_as_one_argument_even_with_thai_letters_and_spaces(tmp_path):
    seen = {}

    def run(command, **kwargs):
        seen["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"bpm": 1, "key": "C major", "key_confidence": 0}), stderr="")

    song = tmp_path / "เพลง ของฉัน.mp3"
    analyze_separately(song, run=run)

    assert seen["command"][-1] == str(song)


def test_a_missing_ffmpeg_in_the_job_is_reported_as_ffmpeg_missing(tmp_path):
    with pytest.raises(FfmpegMissing):
        analyze_separately(tmp_path / "song.m4a", run=_answer(returncode=3, stderr="needs FFmpeg"))


@pytest.mark.parametrize("run", [
    _answer(returncode=1, stderr="Traceback ... ValueError: boom"),
    _answer(stdout="not json"),
    _answer(stdout=""),
])
def test_a_job_that_fails_raises_with_the_reason(tmp_path, run):
    with pytest.raises(AnalysisFailed):
        analyze_separately(tmp_path / "song.mp3", run=run)


def test_a_job_that_hangs_is_given_up_on_instead_of_blocking_forever(tmp_path):
    def hangs(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    with pytest.raises(AnalysisFailed):
        analyze_separately(tmp_path / "song.mp3", run=hangs)


def test_a_job_that_cannot_even_report_its_error_still_exits_quietly(tmp_path, monkeypatch):
    # A windowed build started without a pipe has no usable stderr: printing the traceback raises OSError, which
    # used to escape and open an "Unhandled exception" dialog on the person's screen.
    def cannot_print(*args, **kwargs):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr("core.analysis.traceback.print_exc", cannot_print)

    assert run_job([str(tmp_path / "no-such-song.wav")]) == 1


def test_the_job_prints_one_json_line_the_parent_can_read(tmp_path, capsys):
    song = write_click_track(tmp_path / "clicks.wav", bpm=120)

    assert run_job([str(song)]) == 0

    reply = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert reply["bpm"] == pytest.approx(120, abs=1)
    assert set(reply) == {"bpm", "key", "key_confidence"}   # a click track has no pitch, so its key may be empty
