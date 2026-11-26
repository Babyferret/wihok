from core.model import is_model_cached


def _hf_cache(base, with_weights: bool = True):
    """A Hugging Face cache laid out the way huggingface_hub writes it, holding the htdemucs files."""
    repo = base / "models--adefossez--HTDemucs"
    snapshot = repo / "snapshots" / "abc123"
    snapshot.mkdir(parents=True)
    (repo / "refs").mkdir()
    (repo / "refs" / "main").write_text("abc123")
    (snapshot / "htdemucs.yaml").write_text("models: ['sig12345']\nweights: [[1, 1, 1, 1]]\n")
    if with_weights:
        (snapshot / "sig12345.safetensors").write_bytes(b"weights")
    return base


def _nothing_else(tmp_path):
    """An empty stand-in for the older download location, so a test never sees this computer's real one."""
    nowhere = tmp_path / "no-older-cache"
    nowhere.mkdir()
    return nowhere


def test_the_model_counts_as_cached_when_its_description_and_weights_are_present(tmp_path):
    cache = _hf_cache(tmp_path / "hf")
    assert is_model_cached(cache_dir=cache, torch_checkpoints=_nothing_else(tmp_path)) is True


def test_the_model_is_not_cached_when_the_weights_are_missing(tmp_path):
    cache = _hf_cache(tmp_path / "hf", with_weights=False)
    assert is_model_cached(cache_dir=cache, torch_checkpoints=_nothing_else(tmp_path)) is False


def test_the_model_is_not_cached_in_an_empty_cache(tmp_path):
    (tmp_path / "hf").mkdir()
    assert is_model_cached(cache_dir=tmp_path / "hf", torch_checkpoints=_nothing_else(tmp_path)) is False


def test_trouble_reading_demucs_file_list_means_not_cached_not_a_crash(tmp_path, monkeypatch):
    # e.g. a Demucs upgrade whose files.txt no longer lists a signature: the check must say "not cached" (the person
    # sees the download notice) rather than abort the whole separation with an unrelated error.
    def broken():
        raise KeyError("a signature missing from files.txt")

    monkeypatch.setattr("core.model._older_file_names", broken)
    (tmp_path / "hf").mkdir()

    assert is_model_cached(cache_dir=tmp_path / "hf", torch_checkpoints=_nothing_else(tmp_path)) is False


def test_the_model_counts_as_cached_when_it_came_from_the_older_download_source(tmp_path):
    # When Hugging Face cannot be reached, Demucs downloads the same model from Meta's server instead and
    # keeps it under torch's checkpoints folder. 955717e8-8726e21a.th is its name in demucs/remote/files.txt.
    older = tmp_path / "torch-checkpoints"
    older.mkdir()
    (older / "955717e8-8726e21a.th").write_bytes(b"weights")
    (tmp_path / "hf").mkdir()

    assert is_model_cached(cache_dir=tmp_path / "hf", torch_checkpoints=older) is True
