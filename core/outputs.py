import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputPlan:
    directory: Path
    reuse: bool


def plan_output(song: Path, base: Path) -> OutputPlan:
    directory = Path(base) / f"{song.stem}-{_content_hash(song)}"
    finished = all(
        (directory / f"{song.stem}_{kind}.wav").exists() for kind in ("acapella", "karaoke")
    )
    return OutputPlan(directory=directory, reuse=finished)


def _content_hash(song: Path) -> str:
    digest = hashlib.sha256()
    with open(song, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()[:8]
