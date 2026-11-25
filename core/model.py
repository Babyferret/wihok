"""Knowing whether the separation model is already on this computer.

Demucs fetches `htdemucs` from Hugging Face the first time it is used and keeps it in the standard
Hugging Face cache. The weights are not shipped with Wihok (their license is unclear), so on a new
computer the first separation includes an 80 MB download and the app should say so.
"""
from pathlib import Path

import yaml
from huggingface_hub import try_to_load_from_cache

from core.separator import SeparationError

# Where Demucs publishes htdemucs (see demucs/hf.py: namespace adefossez, repo HTDemucs).
REPO_ID = "adefossez/HTDemucs"
DESCRIPTION_FILE = "htdemucs.yaml"


class ModelDownloadFailed(SeparationError):
    """Separation failed on a computer that did not have the model yet, so the usual cause is the download."""


def is_model_cached(cache_dir: Path | None = None) -> bool:
    """True when the model's description and every weights file it lists are in the cache."""
    description = try_to_load_from_cache(REPO_ID, DESCRIPTION_FILE, cache_dir=cache_dir)
    if not isinstance(description, str):
        return False
    signatures = yaml.safe_load(Path(description).read_text(encoding="utf-8"))["models"]
    return all(
        isinstance(try_to_load_from_cache(REPO_ID, f"{signature}.safetensors", cache_dir=cache_dir), str)
        for signature in signatures
    )
