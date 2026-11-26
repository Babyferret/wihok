import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.analysis import analyze_separately
from core.audio import ensure_decodable
from core.models import AnalysisResult
from core.outputs import plan_output
from core.model import ModelDownloadFailed, is_model_cached
from core.separator import OutOfGpuMemory, Runner, SeparationCancelled, SeparationError, run_demucs, separate


@dataclass(frozen=True)
class ProcessedSong:
    directory: Path
    vocals: Path
    instrumental: Path
    analysis: AnalysisResult
    reused: bool


def process_song(
    song: Path,
    base: Path,
    device: str = "cuda",
    *,
    runner: Runner = run_demucs,
    cancel: threading.Event | None = None,
    on_stage: Callable[[str], None] = lambda stage: None,
    on_notice: Callable[[str], None] = lambda message: None,
    model_cached: Callable[[], bool] = is_model_cached,
    analyzer: Callable[[Path], AnalysisResult] = analyze_separately,
) -> ProcessedSong:
    song = Path(song)
    ensure_decodable(song)
    plan = plan_output(song, base)

    if plan.reuse:
        on_stage("reusing")
        vocals = plan.directory / f"{song.stem}_acapella.wav"
        instrumental = plan.directory / f"{song.stem}_karaoke.wav"
    else:
        first_run = not model_cached()
        on_stage("downloading_model" if first_run else "separating")
        try:
            stems = separate(song, plan.directory, device, runner=runner, cancel=cancel, on_notice=on_notice)
        except (SeparationCancelled, OutOfGpuMemory):
            raise
        except SeparationError as error:
            if first_run:
                raise ModelDownloadFailed(str(error)) from error
            raise
        vocals, instrumental = stems.vocals, stems.instrumental

    on_stage("analyzing")
    return ProcessedSong(
        directory=plan.directory,
        vocals=vocals,
        instrumental=instrumental,
        analysis=analyzer(song),
        reused=plan.reuse,
    )
