import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.models import SeparationResult

MODEL = "htdemucs"
# After an out-of-memory failure, retry with these shorter segments (seconds), in order.
RETRY_SEGMENTS = (5, 3)


class SeparationError(RuntimeError):
    pass


class OutOfGpuMemory(SeparationError):
    """Every segment size ran out of GPU memory. Falling back to the CPU is the caller's decision."""


class SeparationCancelled(SeparationError):
    pass


@dataclass(frozen=True)
class RunOutcome:
    returncode: int
    stderr: str


Runner = Callable[[list[str], threading.Event], RunOutcome]


def run_demucs(cmd: list[str], cancel: threading.Event) -> RunOutcome:
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    while True:
        try:
            _, stderr = process.communicate(timeout=0.2)
            return RunOutcome(returncode=process.returncode, stderr=stderr)
        except subprocess.TimeoutExpired:
            if cancel.is_set():
                process.kill()
                _, stderr = process.communicate()
                return RunOutcome(returncode=process.returncode, stderr=stderr)


def separate(
    input_path: Path,
    out_dir: Path,
    device: str = "cuda",
    *,
    runner: Runner = run_demucs,
    cancel: threading.Event | None = None,
    on_notice: Callable[[str], None] = lambda message: None,
) -> SeparationResult:
    input_path, out_dir = Path(input_path), Path(out_dir)
    cancel = cancel or threading.Event()
    out_dir_existed = out_dir.exists()
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = out_dir / ".demucs-work"

    def clean_up():
        shutil.rmtree(work_dir, ignore_errors=True)
        if not out_dir_existed and not any(out_dir.iterdir()):
            out_dir.rmdir()

    outcome = None
    for segment in (None, *RETRY_SEGMENTS):
        if segment is not None:
            on_notice(f"The GPU ran out of memory. Trying again with {segment}-second segments.")
        cmd = _command(input_path, work_dir, device, segment)
        outcome = runner(cmd, cancel)
        if cancel.is_set():
            clean_up()
            raise SeparationCancelled()
        if outcome.returncode == 0:
            break
        if "out of memory" not in outcome.stderr.lower():
            break
    if outcome.returncode != 0:
        clean_up()
        message = outcome.stderr[-500:]
        if "out of memory" in outcome.stderr.lower():
            raise OutOfGpuMemory(message)
        raise SeparationError(message)

    stems = work_dir / MODEL / input_path.stem
    vocals = out_dir / f"{input_path.stem}_acapella.wav"
    instrumental = out_dir / f"{input_path.stem}_karaoke.wav"
    shutil.move(stems / "vocals.wav", vocals)
    shutil.move(stems / "no_vocals.wav", instrumental)
    shutil.rmtree(work_dir)
    return SeparationResult(vocals=vocals, instrumental=instrumental)


def _command(input_path: Path, work_dir: Path, device: str, segment: int | None) -> list[str]:
    # A packaged app has no python.exe to run `-m demucs`, so it starts itself in demucs mode (see main.py).
    launcher = [sys.executable, "--demucs"] if getattr(sys, "frozen", False) else [sys.executable, "-m", "demucs"]
    cmd = launcher + ["--two-stems=vocals", "-n", MODEL, "-d", device]
    if segment is not None:
        cmd += ["--segment", str(segment)]
    return cmd + ["-o", str(work_dir), str(input_path)]
