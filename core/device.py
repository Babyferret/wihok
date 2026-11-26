"""Which device Demucs should run on, found without loading PyTorch into the program's own process.

Importing torch costs hundreds of MB of memory, which the window would hold for as long as it is open, so the
window only guesses from files (looks_cuda_capable) and asks a short-lived second process to confirm (probe_device).
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

PROBE_TIMEOUT_SECONDS = 60


def _system_dir() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"


def torch_lib_dir() -> Optional[Path]:
    """Where PyTorch's libraries are, found without importing it."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "_internal" / "torch" / "lib"
    spec = importlib.util.find_spec("torch")
    return Path(spec.origin).parent / "lib" if spec and spec.origin else None


def looks_cuda_capable(system_dir: Optional[Path] = None, torch_lib: Optional[Path] = None) -> bool:
    """A quick guess: an NVIDIA driver is installed (nvcuda.dll) and this build of PyTorch has CUDA in it."""
    system_dir = system_dir or _system_dir()
    torch_lib = torch_lib or torch_lib_dir()
    if torch_lib is None:
        return False
    if getattr(sys, "frozen", False) and not (Path(sys.executable).parent / "gpu-pack.txt").exists():
        # torch_cuda.dll can be left behind when the GPU add-on is replaced by the CPU files; the add-on's marker
        # file (which the installer deletes in that case) is what says GPU support is really installed.
        return False
    return (system_dir / "nvcuda.dll").exists() and (torch_lib / "torch_cuda.dll").exists()


def probe_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--device"]
    return [sys.executable, "-m", "core.device"]


def probe_device(command: Optional[list[str]] = None, run: Callable = subprocess.run) -> str:
    """Ask a second process what PyTorch sees. Any trouble means "cpu": a wrong "cuda" would make the job fail."""
    try:
        done = run(command or probe_command(), capture_output=True, text=True, timeout=PROBE_TIMEOUT_SECONDS,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return "cpu"
    lines = done.stdout.split() if done.returncode == 0 and done.stdout else []
    return "cuda" if lines and lines[-1] == "cuda" else "cpu"


def print_device() -> int:
    import torch

    print("cuda" if torch.cuda.is_available() else "cpu")
    return 0


if __name__ == "__main__":
    sys.exit(print_device())
