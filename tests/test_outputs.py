from core.outputs import plan_output


def test_same_name_with_different_content_gets_its_own_folder(tmp_path):
    first = tmp_path / "a" / "song.mp3"
    second = tmp_path / "b" / "song.mp3"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"one song")
    second.write_bytes(b"a different song")
    base = tmp_path / "Wihok"

    plan_first = plan_output(first, base)
    plan_second = plan_output(second, base)

    assert plan_first.directory != plan_second.directory
    assert plan_first.directory.parent == base
    assert plan_first.directory.name.startswith("song-")
    assert plan_output(first, base).directory == plan_first.directory


def test_reuses_finished_results_but_not_half_finished_ones(tmp_path):
    song = tmp_path / "song.mp3"
    song.write_bytes(b"one song")
    base = tmp_path / "Wihok"

    plan = plan_output(song, base)
    assert plan.reuse is False

    plan.directory.mkdir(parents=True)
    (plan.directory / "song_acapella.wav").write_bytes(b"x")
    assert plan_output(song, base).reuse is False

    (plan.directory / "song_karaoke.wav").write_bytes(b"x")
    assert plan_output(song, base).reuse is True
