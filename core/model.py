"""Knowing whether the separation model is already on this computer.

Demucs fetches `htdemucs` the first time it is used. It tries Hugging Face first and keeps the files in the
standard Hugging Face cache. If Hugging Face cannot be reached it falls back to the older download from
Meta's server and keeps that file under torch's checkpoints folder instead. Either one counts.

The weights are not shipped with Wihok (their license is unclear), so on a new computer the first separation
includes an 80 MB download and the app should say so, and only that once.
"""
import os
from pathlib import Path

import yaml
from huggingface_hub import try_to_load_from_cache

from core.separator import SeparationError

# Where Demucs publishes htdemucs (see demucs/hf.py: namespace adefossez, repo HTDemucs).
REPO_ID = "adefossez/HTDemucs"
DESCRIPTION_FILE = "htdemucs.yaml"


class ModelDownloadFailed(SeparationError):
    """Separation failed on a computer that did not have the model yet, so the usual cause is the download."""


def is_model_cached(cache_dir: Path | None = None, torch_checkpoints: Path | None = None) -> bool:
    """True when the model is in the Hugging Face cache or in torch's cache from the older download."""
    return _in_hugging_face_cache(cache_dir) or _in_older_cache(torch_checkpoints)


def _in_hugging_face_cache(cache_dir: Path | None) -> bool:
    description = try_to_load_from_cache(REPO_ID, DESCRIPTION_FILE, cache_dir=cache_dir)
    if not isinstance(description, str):
        return False
    signatures = yaml.safe_load(Path(description).read_text(encoding="utf-8"))["models"]
    return all(
        isinstance(try_to_load_from_cache(REPO_ID, f"{signature}.safetensors", cache_dir=cache_dir), str)
        for signature in signatures
    )


def _in_older_cache(checkpoints: Path | None) -> bool:
    try:
        names = _older_file_names()
    except (ImportError, OSError, KeyError, ValueError, TypeError, yaml.YAMLError):
        # A cache check must never abort a separation: if Demucs' file list cannot be read, say "not cached" and
        # the person simply sees the download notice.
        return False
    return all((Path(checkpoints or _torch_checkpoints_dir()) / name).is_file() for name in names)


def _torch_checkpoints_dir() -> Path:
    """Where torch keeps downloaded checkpoints (the rule of torch.hub.get_dir), found without importing torch:
    this runs in the window's own process, and loading torch there would hold hundreds of MB while idle."""
    home = os.environ.get("TORCH_HOME") or Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "torch"
    return Path(os.path.expanduser(home)) / "hub" / "checkpoints"


def _older_file_names() -> list[str]:
    """The file names Demucs saves the older download under, taken from the files Demucs itself ships.
    Read from those files directly: importing demucs.pretrained would load torch."""
    import demucs

    remote = Path(demucs.__file__).parent / "remote"
    file_for_signature = {}
    for line in (remote / "files.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "root:")):
            file_for_signature[line.split("-", 1)[0]] = line
    signatures = yaml.safe_load((remote / "htdemucs.yaml").read_text(encoding="utf-8"))["models"]
    return [file_for_signature[signature] for signature in signatures]
