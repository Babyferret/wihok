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


def test_the_model_counts_as_cached_when_its_description_and_weights_are_present(tmp_path):
    assert is_model_cached(cache_dir=_hf_cache(tmp_path)) is True


def test_the_model_is_not_cached_when_the_weights_are_missing(tmp_path):
    assert is_model_cached(cache_dir=_hf_cache(tmp_path, with_weights=False)) is False


def test_the_model_is_not_cached_in_an_empty_cache(tmp_path):
    assert is_model_cached(cache_dir=tmp_path) is False
