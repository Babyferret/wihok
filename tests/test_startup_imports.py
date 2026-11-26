"""The window must stay light while it sits idle: PyTorch and the audio-analysis libraries belong to the jobs that
use them (a separate process for Demucs), not to the program the person keeps open. Loading them cost 640 MB."""
import json
import os
import subprocess
import sys
from pathlib import Path

HEAVY = ["torch", "librosa", "numba", "scipy", "sklearn", "demucs.pretrained"]
ROOT = Path(__file__).resolve().parent.parent

SCRIPT = """
import json, sys
from PySide6.QtWidgets import QApplication
app = QApplication([])
from ui.main_window import MainWindow
window = MainWindow(device="cpu")
window.show()
app.processEvents()
import tempfile
from core.model import is_model_cached   # what the worker calls when a song starts
# an empty Hugging Face cache sends the check on to the older download location, which is where torch used to be loaded
is_model_cached(cache_dir=tempfile.mkdtemp())
print(json.dumps([name for name in %r if name in sys.modules]))
""" % (HEAVY,)


def test_the_idle_window_and_the_model_check_load_none_of_the_heavy_libraries():
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    done = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)

    assert done.returncode == 0, done.stderr[-800:]
    assert json.loads(done.stdout.strip().splitlines()[-1]) == []
