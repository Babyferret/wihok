"""main.py's --demucs mode: how a packaged app runs the separation."""
import subprocess
import sys
from pathlib import Path

import pytest

from core.model import is_model_cached
from tests.synth import write_chord

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(not is_model_cached(), reason="needs the htdemucs model in the Hugging Face cache")
@pytest.mark.parametrize("name", ["song", "เพลงทดสอบ", "日本語のテスト"])
def test_the_worker_separates_a_song_whatever_its_name(tmp_path, name, monkeypatch):
    # The worker is a separate process; make it use a legacy code page like many PCs do.
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    song = write_chord(tmp_path / f"{name}.wav", [60, 64, 67], seconds=4)
    out = tmp_path / "out"

    done = subprocess.run(
        [sys.executable, "main.py", "--demucs", "--two-stems=vocals", "-n", "htdemucs", "-d", "cpu",
         "-o", str(out), str(song)],
        cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace",
    )

    assert done.returncode == 0, done.stderr[-400:]
    assert (out / "htdemucs" / name / "vocals.wav").exists()
