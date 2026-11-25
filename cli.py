"""Temporary command-line front end, used to check that core works on real songs."""
import argparse
import signal
import sys
import threading
from pathlib import Path

import torch

from core.audio import FfmpegMissing
from core.model import ModelDownloadFailed
from core.pipeline import process_song
from core.separator import OutOfGpuMemory, SeparationCancelled, SeparationError

DEFAULT_OUTPUT = Path.home() / "Music" / "Wihok"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Split a song into karaoke and acapella, and find its BPM and key.")
    parser.add_argument("song", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help=f"results folder (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--device", choices=["cuda", "cpu"], help="default: cuda when available")
    args = parser.parse_args(argv)

    if not args.song.is_file():
        print(f"File not found: {args.song}", file=sys.stderr)
        return 2

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    if device == "cpu":
        print("Running on the CPU. This is much slower than the GPU.")

    cancel = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: cancel.set())

    try:
        done = _process(args.song, args.out, device, cancel)
    except SeparationCancelled:
        print("Cancelled. Partial files were removed.")
        return 130
    except FfmpegMissing as error:
        print(f"{error} Install FFmpeg, or use an mp3, wav or flac file.", file=sys.stderr)
        return 1
    except ModelDownloadFailed:
        print("The separation model has not been downloaded yet and the download failed. "
              "Check your internet connection and try again.", file=sys.stderr)
        return 1
    except SeparationError as error:
        print(f"Separation failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # an unreadable file, for example: report it without a traceback
        print(f"Could not process this file: {error}", file=sys.stderr)
        return 1

    print(f"BPM: {done.analysis.bpm:.1f}")
    print(f"Key: {done.analysis.key} (confidence {done.analysis.key_confidence:.2f})")
    print(f"Karaoke:  {done.instrumental}")
    print(f"Acapella: {done.vocals}")
    return 0


STAGE_MESSAGES = {
    "reusing": "Results already exist, reusing them.",
    "downloading_model": "First time: downloading the separation model (about 80 MB, needs internet, happens once)...",
    "separating": "Separating...",
    "analyzing": "Analysing BPM and key...",
}


def _process(song: Path, base: Path, device: str, cancel: threading.Event):
    def run(on: str):
        return process_song(
            song, base, on, cancel=cancel,
            on_stage=lambda stage: print(STAGE_MESSAGES[stage]), on_notice=print,
        )

    try:
        return run(device)
    except OutOfGpuMemory:
        if device != "cuda":
            raise
        answer = input("The GPU is out of memory. Try the CPU? It is much slower. [y/N] ")
        if answer.strip().lower() != "y":
            raise
        return run("cpu")


if __name__ == "__main__":
    sys.exit(main())
