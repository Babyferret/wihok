import subprocess
import sys

import pytest

from core.device import looks_cuda_capable, probe_device


def _dirs(tmp_path, nvcuda: bool, torch_cuda: bool):
    system, torch_lib = tmp_path / "system32", tmp_path / "torch" / "lib"
    system.mkdir()
    torch_lib.mkdir(parents=True)
    if nvcuda:
        (system / "nvcuda.dll").write_bytes(b"")
    if torch_cuda:
        (torch_lib / "torch_cuda.dll").write_bytes(b"")
    return system, torch_lib


@pytest.mark.parametrize("nvcuda,torch_cuda,expected", [
    (True, True, True),
    (True, False, False),   # the CPU build of PyTorch
    (False, True, False),   # CUDA build, but no NVIDIA driver
    (False, False, False),
])
def test_guesses_cuda_from_the_driver_and_the_pytorch_build_without_loading_pytorch(tmp_path, nvcuda, torch_cuda, expected):
    system, torch_lib = _dirs(tmp_path, nvcuda, torch_cuda)

    assert looks_cuda_capable(system_dir=system, torch_lib=torch_lib) is expected


def test_an_installed_program_counts_as_cuda_only_with_the_add_on_marker(tmp_path, monkeypatch):
    # An orphaned torch_cuda.dll can stay behind when the GPU add-on is replaced by the CPU files; the marker file
    # the add-on writes (and the installer deletes then) is what says GPU support is really there.
    system, torch_lib = _dirs(tmp_path, nvcuda=True, torch_cuda=True)
    app = tmp_path / "app"
    app.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(app / "Wihok.exe"))

    assert looks_cuda_capable(system_dir=system, torch_lib=torch_lib) is False

    (app / "gpu-pack.txt").write_text("2.11.0")
    assert looks_cuda_capable(system_dir=system, torch_lib=torch_lib) is True


def test_no_pytorch_found_means_cpu(tmp_path, monkeypatch):
    system, _ = _dirs(tmp_path, nvcuda=True, torch_cuda=True)
    monkeypatch.setattr("core.device.torch_lib_dir", lambda: None)

    assert looks_cuda_capable(system_dir=system) is False


def _answer(stdout="", returncode=0):
    return lambda command, **kwargs: subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")


@pytest.mark.parametrize("stdout,expected", [("cuda\n", "cuda"), ("cpu\n", "cpu"), ("warning: x\ncuda\n", "cuda")])
def test_the_probe_reports_what_pytorch_says(stdout, expected):
    assert probe_device(["wihok", "--device"], run=_answer(stdout)) == expected


@pytest.mark.parametrize("run", [
    _answer("cuda\n", returncode=1),
    _answer("garbage"),
    _answer(""),
    lambda command, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(command, 1)),
    lambda command, **kwargs: (_ for _ in ()).throw(OSError("cannot start")),
])
def test_when_the_probe_fails_the_answer_is_cpu_never_cuda(run):
    assert probe_device(["wihok", "--device"], run=run) == "cpu"
